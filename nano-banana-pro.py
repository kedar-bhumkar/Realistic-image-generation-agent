import os
import random
import replicate
import requests
import uuid
import re
import base64
import time
from urllib.parse import urlparse
import sys
import io
import json
import mimetypes

# Google Drive API imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

# Ensure you have the following installed:
# pip install replicate requests python-dotenv google-api-python-client google-auth-httplib2 google-auth-oauthlib

class NanoBananaProGenerator:
    def __init__(self, output_dir):
        """
        Initialize the generator with an output directory.
        output_dir: Local path (can be a Google Drive synced folder).
        """
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            print(f"Created output directory: {output_dir}")
        
        # Initialize Replicate client with a higher timeout (e.g., 10 minutes)
        # Pass timeout to the constructor to ensure it applies to the underlying httpx client
        self.client = replicate.Client(
            api_token=os.environ.get("REPLICATE_API_TOKEN"),
            timeout=600.0
        )
        
        # Scope for uploading files to Google Drive and reading input files
        # 'https://www.googleapis.com/auth/drive' is required to rename files not created by this app
        self.SCOPES = [
            'https://www.googleapis.com/auth/drive'
        ]
        self.drive_service = None

    def _authenticate_gdrive(self):
        """Authenticates with Google Drive API using User Credentials (OAuth 2.0)."""
        if self.drive_service:
            return self.drive_service

        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)
            
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing token: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists('credentials.json'):
                    print("Error: 'credentials.json' not found.")
                    print("1. Go to Google Cloud Console > APIs & Services > Credentials")
                    print("2. Create Credentials > OAuth client ID > Desktop app")
                    print("3. Download the JSON, rename it to 'credentials.json' and place it in this folder.")
                    return None
                    
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        try:
            self.drive_service = build('drive', 'v3', credentials=creds)
            return self.drive_service
        except Exception as e:
            print(f"Error authenticating with OAuth: {e}")
            return None

    def _upload_to_gdrive(self, filepath, folder_id):
        """Uploads a file to the specified Google Drive folder."""
        service = self._authenticate_gdrive()
        if not service:
            print("Skipping Google Drive upload due to authentication failure.")
            return

        file_metadata = {
            'name': os.path.basename(filepath),
            'parents': [folder_id]
        }
        
        mime_type, _ = mimetypes.guess_type(filepath)
        if mime_type is None:
            mime_type = 'application/octet-stream'

        media = MediaFileUpload(filepath, mimetype=mime_type, resumable=True)
        
        try:
            print(f"Uploading {os.path.basename(filepath)} to Google Drive...")
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            print(f"File uploaded to Google Drive with ID: {file.get('id')}")
        except Exception as e:
            print(f"Error uploading to Google Drive: {e}")

    def list_files_in_folder(self, folder_id):
        """Lists all image files in a Google Drive folder."""
        service = self._authenticate_gdrive()
        if not service:
            return []
        
        results = []
        page_token = None
        while True:
            try:
                # q parameter to filter by parent folder and image mimeType
                response = service.files().list(
                    q=f"'{folder_id}' in parents and mimeType contains 'image/' and trashed = false",
                    spaces='drive',
                    fields='nextPageToken, files(id, name)',
                    pageToken=page_token
                ).execute()
                
                results.extend(response.get('files', []))
                page_token = response.get('nextPageToken', None)
                if page_token is None:
                    break
            except Exception as e:
                print(f"Error listing files in folder {folder_id}: {e}")
                break
        return results

    def _rename_gdrive_file(self, file_id, new_name):
        """Renames a file in Google Drive."""
        service = self._authenticate_gdrive()
        if not service:
            return False
        
        try:
            body = {'name': new_name}
            service.files().update(fileId=file_id, body=body).execute()
            print(f"Renamed file {file_id} to {new_name}")
            return True
        except Exception as e:
            print(f"Error renaming file {file_id}: {e}")
            return False

    def get_random_image_from_folder(self, folder_id, filter_prefix=None):
        """Pick a random image from a Google Drive folder and return its URL."""
        files = self.list_files_in_folder(folder_id)
        
        if filter_prefix:
            # Filter out files that already contain the prefix
            original_count = len(files)
            files = [f for f in files if filter_prefix not in f['name']]
            print(f"Filtered out {original_count - len(files)} files containing prefix '{filter_prefix}'. Remaining: {len(files)}")
            
        if files:
            selected = random.choice(files)
            
            if filter_prefix:
                # Rename the selected file
                new_name = f"{filter_prefix}{selected['name']}"
                print(f"Renaming selected random image to: {new_name}")
                self._rename_gdrive_file(selected['id'], new_name)
            
            # Construct a URL that _get_gdrive_id can parse
            return f"https://drive.google.com/file/d/{selected['id']}/view?usp=drive_link"
        return None

    def _is_url(self, path):
        try:
            result = urlparse(path)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

    def _is_gdrive_url(self, url):
        return "drive.google.com" in url

    def _get_gdrive_id(self, url):
        patterns = [
            r'/file/d/([a-zA-Z0-9_-]+)',
            r'id=([a-zA-Z0-9_-]+)',
            r'/open\?id=([a-zA-Z0-9_-]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def _download_gdrive_file(self, file_id, destination):
        # Try using authenticated Drive API first
        service = self._authenticate_gdrive()
        if service:
            try:
                # print(f"Attempting to download file ID {file_id} via Google Drive API...")
                request = service.files().get_media(fileId=file_id)
                fh = io.FileIO(destination, 'wb')
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                    # print(f"Download {int(status.progress() * 100)}%.")
                return destination
            except Exception as e:
                print(f"API download failed (might be permissions issue or public file): {e}")
                print("Falling back to public URL download method...")

        # Construct download URL for public files (fallback)
        url = "https://drive.google.com/uc?export=download"
        session = requests.Session()
        
        try:
            response = session.get(url, params={'id': file_id}, stream=True)
            
            token = self._get_confirm_token(response)
            if token:
                params = {'id': file_id, 'confirm': token}
                response = session.get(url, params=params, stream=True)

            if response.status_code == 200:
                with open(destination, 'wb') as f:
                    for chunk in response.iter_content(32768):
                        if chunk:
                            f.write(chunk)
                return destination
            else:
                print(f"Public download failed with status code: {response.status_code}")
        except Exception as e:
            print(f"Error downloading Drive file: {e}")
        return None

    def _get_confirm_token(self, response):
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                return value
        return None

    def _download_web_image(self, url, destination):
        try:
            # First, check headers without downloading content
            response = requests.head(url, allow_redirects=True)
            content_type = response.headers.get('Content-Type', '')
            
            if 'image' not in content_type:
                print(f"Warning: URL {url} does not appear to be an image. Content-Type: {content_type}")
                # For PostImage specifically, it might be a landing page.
                if "postimg.cc" in url and "i.postimg.cc" not in url:
                    print(f"  Tip: For postimg.cc, right-click the image and 'Copy Image Address' to get the direct link (e.g., https://i.postimg.cc/...).")
                return None

            response = requests.get(url, stream=True)
            if response.status_code == 200:
                with open(destination, 'wb') as f:
                    for chunk in response.iter_content(32768):
                        f.write(chunk)
                return destination
        except Exception as e:
            print(f"Error downloading web image: {e}")
        return None

    def image_to_data_url(self, image_path):
        """
        Convert an image file to a data URL.
        """
        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                # Determine the image type from the file extension
                image_type = os.path.splitext(image_path)[1].lower().replace('.', '')
                if image_type == 'jpg':
                    image_type = 'jpeg'
                return f"data:image/{image_type};base64,{encoded_string}"
        except Exception as e:
            print(f"Error converting image to data URL: {e}")
            return None

    def prepare_image(self, image_path_or_url):
        """
        Prepares an image for processing.
        Returns a data URL string or None if failed.
        """
        local_path = None

        # If it's a local file
        if not self._is_url(image_path_or_url):
            if os.path.exists(image_path_or_url):
                local_path = image_path_or_url
            else:
                print(f"File not found: {image_path_or_url}")
                return None
        else:
            # It's a URL - download it first to convert to data URL
            cache_dir = os.path.join(self.output_dir, "cache")
            os.makedirs(cache_dir, exist_ok=True)
            
            filename = f"{uuid.uuid4()}.tmp"
            destination = os.path.join(cache_dir, filename)

            if self._is_gdrive_url(image_path_or_url):
                file_id = self._get_gdrive_id(image_path_or_url)
                if file_id:
                    print(f"Downloading Google Drive file ID: {file_id}...")
                    local_path = self._download_gdrive_file(file_id, destination)
                else:
                    print(f"Could not parse Drive ID from: {image_path_or_url}")
            else:
                print(f"Downloading image from: {image_path_or_url}...")
                local_path = self._download_web_image(image_path_or_url, destination)

        if local_path:
            return self.image_to_data_url(local_path)
        return None

    def generate(self, prompts, images, model_version="google/nano-banana-pro", saveRemotely=False, drive_folder_id=None, input_config=None):
        """
        prompts: List of prompt strings.
        images: List of image paths or URLs.
        saveRemotely: Boolean flag to save to Google Drive.
        drive_folder_id: Google Drive folder ID to save to.
        input_config: Dictionary of input arguments for the model (e.g. resolution, aspect_ratio, etc.)
        """
        if not os.environ.get("REPLICATE_API_TOKEN"):
            print("Error: REPLICATE_API_TOKEN environment variable is not set.")
            return

        # Prepare images
        input_data_urls = []
        for img in images:
            data_url = self.prepare_image(img)
            if data_url:
                input_data_urls.append(data_url)
        
        if not input_data_urls and images:
            print("Warning: Input images were provided but none could be loaded.")
        
        # Processing
        start_total = time.time()
        times = []

        for prompt in prompts:
            print(f"\nProcessing prompt: '{prompt}'")
            start_image = time.time()
            try:
                # Prepare input arguments for this specific run
                # Start with the config from Supabase (or empty dict)
                input_args = input_config.copy() if input_config else {}
                
                # Determine keys based on model_config (input_args)
                image_key = input_args.get("image_key", "image_input")
                prompt_key = "prompt"

                # Remove the 'image_key' from input_args as it's not a valid argument for the model
                if "image_key" in input_args:
                    del input_args["image_key"]
                    
                # Add dynamic arguments using the determined keys
                input_args[prompt_key] = prompt
                
                if input_data_urls:                                       
                        input_args[image_key] = input_data_urls
                
                # Remove keys that are not valid input arguments if they slipped in (like model_version)
                if "model_version" in input_args:
                    del input_args["model_version"]

                print(f"Input arguments: {model_version}")
                print("Sending request to Replicate...")
                # Note: If the model version hash is needed, replicate.run handles "owner/name" 
                # by fetching the latest version automatically.
                # Use self.client.run instead of replicate.run to use the custom timeout
                output = self.client.run(
                    model_version,
                    input=input_args
                )
                
                # Save results
                # Output can be a single item or list
                if isinstance(output, list):
                    for item in output:
                        self._save_output(item, saveRemotely, drive_folder_id)
                else:
                    self._save_output(output, saveRemotely, drive_folder_id)

            except Exception as e:
                print(f"Error during generation: {e}")
            
            end_image = time.time()
            duration = end_image - start_image
            times.append(duration)
            print(f"Time for this image: {duration:.2f} seconds")

        end_total = time.time()
        total_duration = end_total - start_total
        avg_duration = sum(times) / len(times) if times else 0
        
        print(f"\nTotal time: {total_duration:.2f} seconds")
        print(f"Average time per image: {avg_duration:.2f} seconds")

        # Cleanup (optional)
        # Note: We are no longer opening file handles that need closing, 
        # but we might want to clean up temp files if we tracked them.
        pass

    def _save_output(self, output_obj, saveRemotely=False, drive_folder_id=None):
        url = str(output_obj)
        if hasattr(output_obj, 'url'):
            url = output_obj.url

        # Determine extension
        ext = "webp" # Common default for Replicate
        # Try to guess from URL
        path = urlparse(url).path
        if "." in path:
            ext = path.split(".")[-1]

        filename = f"{uuid.uuid4()}.{ext}"
        filepath = os.path.join(self.output_dir, filename)
        
        print(f"Saving output to {filepath}...")
        try:
            response = requests.get(url)
            if response.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(response.content)
                print("Image saved successfully.")
                
                # Upload to Google Drive if flag is set
                if saveRemotely and drive_folder_id:
                    self._upload_to_gdrive(filepath, drive_folder_id)
                elif saveRemotely and not drive_folder_id:
                    print("Warning: saveRemotely is True but drive_folder_id is missing.")
                    
            else:
                print(f"Failed to download output image: Status {response.status_code}")
        except Exception as e:
            print(f"Error saving file: {e}")

# Example Usage
if __name__ == "__main__":
    # You can customize these inputs
    prompts = [ 
"Keeping a consistent face and clothing, show the man and woman wearing a low waist saree, showing midriff and deep navel, holding hands in the rain."

    ]
    
    # Add your image paths or URLs here
    input_images = [
        # "https://example.com/image.jpg", 
        # "path/to/local/image.png"
        #  "C:\\DDrive\\Programming\\Project\\misc\\consistent character generator\\input\\ComfyUI_01208_.png",         
        #  "C:\\DDrive\\Programming\\Project\\misc\\consistent character generator\\input\\ComfyUI_00627_-topaz-face-color-upscale-4x.png",
             #"https://www.koimoi.com/wp-content/new-galleries/2025/11/madhuri-dixit-on-pay-disparity-01.jpg",
             #"https://i.pinimg.com/564x/17/13/af/1713af39d3478e58c768ec6e6e80a002.jpg",
             #"https://i.postimg.cc/JzPqhJFr/Screenshot-2025-02-28-110258-topaz-face-upscale-3-5x.png",
             #"https://i.pinimg.com/originals/4b/ea/82/4bea82989b65888ff1f1efbae914f182.jpg",
            #  "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEi7EBGg16Z-vgA6N4DmRgra8t6fo8yzWru5hzXUxBkgdyky3_YzY7vC9LT5iEbGrGNwmC_VVpBh2iDj18AyD25zFoEiYs6Mo8RB9ANwAzLahiN5JNKkIQAF0n6LcI7FrrDqOYuwBJWp6hs/s1600/Sailaab+001.jpg",
            #"https://i.postimg.cc/d16QV3VC/Comfy-UI-00119.png",
             #"https://i.postimg.cc/cHdK1V0W/replicate-prediction-tqtd8x8desrmc0csfx7t4jmhm8.webp",
             #"https://i.pinimg.com/474x/88/09/55/8809556004f184b1234f45842e058e21.jpg",
             #"https://i.postimg.cc/G3kPSx9m/Comfy-UI-01210.png"
             #"C:\\DDrive\\Programming\\Project\\misc\\nano-banana-pro-api\\input\\f015534def5bd4ef7d8ceca0f99976ab.jpg",
             #"C:\\DDrive\\Programming\\Project\\misc\\nano-banana-pro-api\\input\\replicate-prediction-9qc88r7g7hrm80csg4kt8szcm8.jpg"
             #"https://drive.google.com/file/d/1FAjsSA1PJRiqYjTqvUi_iMdQ5nzE-jW5/view?usp=drive_link",
             #"https://drive.google.com/file/d/196uSzA4fUe9T13NHcWO8KijdWpPr7YWZ/view?usp=drive_link"
            
  "https://drive.google.com/file/d/19lwb1fYk2B15N7Y8vJW3LvfSmjz-YuNb/view?usp=drive_link",
  "https://drive.google.com/file/d/1PeafMQFtIrOASlSEhVH0gAYs8bf85voU/view?usp=drive_link"
]
         
    
    # Output location
    output_folder = "output/nano_banana_results"
    
    # Remote Save Configuration
    saveRemotely = True
    drive_folder_id = "1H4wWGNaY01skMzUvQtQmHWlabaTc4rHx"    
    

    generator = NanoBananaProGenerator(output_folder)
    
    if input_images or prompts:
         generator.generate(prompts, input_images, saveRemotely=saveRemotely, drive_folder_id=drive_folder_id)
    else:
        print("Please configure 'prompts' and 'input_images' in the script to run.")


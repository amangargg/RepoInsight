import os
import subprocess
import uuid
import re

class GitHubService:
    @staticmethod
    def is_valid_github_url(url: str) -> bool:
        """Simple regex check for a valid GitHub repository URL."""
        pattern = r"^https?://(www\.)?github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?$"
        return bool(re.match(pattern, url))

    @staticmethod
    def clone_repository(github_url: str, base_dir: str = "./repositories") -> str:
        """Clone a public GitHub repository locally and return its absolute path.
        
        Args:
            github_url (str): The URL of the repository to clone.
            base_dir (str): Base folder where cloned repositories will be stored.
        """
        github_url = github_url.strip().rstrip("/")
        if not GitHubService.is_valid_github_url(github_url):
            raise ValueError(f"Invalid GitHub URL: '{github_url}'")

        # Create unique folder name: repo_name_uuid
        repo_name = github_url.split("/")[-1]
        unique_id = uuid.uuid4().hex[:8]
        dest_folder_name = f"{repo_name}_{unique_id}"
        
        os.makedirs(base_dir, exist_ok=True)
        dest_path = os.path.abspath(os.path.join(base_dir, dest_folder_name))

        # Execute git clone
        print(f"Cloning {github_url} into {dest_path}...")
        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", github_url, dest_path],
                capture_output=True,
                text=True,
                check=True,
                timeout=180  # 3-minute timeout
            )
            print("Successfully cloned repository.")
            return dest_path
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"Cloning timed out: {e}")
        except subprocess.CalledProcessError as e:
            # Extract clean error message from stderr
            stderr_err = e.stderr or "Unknown git error"
            raise RuntimeError(f"Failed to clone repository: {stderr_err.strip()}")

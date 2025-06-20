#!/bin/bash

# File to store GitHub credentials
CREDENTIALS_FILE="$HOME/.github_credentials"

# Function to set up GitHub credentials
setup_credentials() {
  echo "Setting up GitHub credentials..."
  
  # Prompt for GitHub username and token if not already set
  if [ ! -f "$CREDENTIALS_FILE" ]; then
    read -p "Enter your GitHub username: " GITHUB_USERNAME
    read -p "Enter your GitHub personal access token: " GITHUB_TOKEN
    
    # Save credentials to file
    echo "GITHUB_USERNAME=$GITHUB_USERNAME" > "$CREDENTIALS_FILE"
    echo "GITHUB_TOKEN=$GITHUB_TOKEN" >> "$CREDENTIALS_FILE"
    
    # Set file permissions to be secure
    chmod 600 "$CREDENTIALS_FILE"
    
    echo "Credentials saved to $CREDENTIALS_FILE"
  else
    echo "Credentials already exist at $CREDENTIALS_FILE"
  fi
  
  # Load credentials
  source "$CREDENTIALS_FILE"
}

# Function to create a new repository
create_repository() {
  # Check if repository name was provided
  if [ -z "$1" ]; then
    echo "Error: Repository name is required."
    echo "Usage: $0 <repository_name> [description]"
    exit 1
  fi
  
  REPO_NAME="$1"
  REPO_DESCRIPTION="${2:-Repository created from RHEL}"
  
  echo "Creating repository: $REPO_NAME"
  
  # Create the repository on GitHub
  RESPONSE=$(curl -s -L \
    -X POST \
    -H "Accept: application/vnd.github+json" \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    https://api.github.com/user/repos \
    -d "{\"name\":\"$REPO_NAME\",\"description\":\"$REPO_DESCRIPTION\",\"private\":false}")
  
  # Check for errors
  if echo "$RESPONSE" | grep -q "errors"; then
    echo "Error creating repository on GitHub:"
    echo "$RESPONSE"
    exit 1
  fi
  
  echo "Repository created successfully on GitHub."
}

# Function to initialize local repository and push to GitHub
init_and_push() {
  REPO_NAME="$1"
  
  # Initialize git repository if .git directory doesn't exist
  if [ ! -d ".git" ]; then
    echo "Initializing local Git repository..."
    git init
  else
    echo "Git repository already initialized."
  fi
  
  # Add all files
  echo "Adding files to Git..."
  git add .
  
  # Commit files
  echo "Committing files..."
  git commit -m "Initial commit"
  
  # Add remote origin
  echo "Setting up remote repository..."
  git remote remove origin 2>/dev/null || true
  git remote add origin "https://$GITHUB_TOKEN@github.com/$GITHUB_USERNAME/$REPO_NAME.git"
  
  # Push to GitHub
  echo "Pushing to GitHub..."
  git push -u origin $(git branch --show-current)
  
  echo "Repository '$REPO_NAME' has been successfully created and pushed to GitHub."
}

# Main execution
setup_credentials

# If repository name was provided as argument
if [ ! -z "$1" ]; then
  create_repository "$1" "$2"
  init_and_push "$1"
else
  # If no argument, prompt for repository name
  read -p "Enter new repository name: " REPO_NAME
  read -p "Enter repository description (optional): " REPO_DESCRIPTION
  
  create_repository "$REPO_NAME" "$REPO_DESCRIPTION"
  init_and_push "$REPO_NAME"
fi

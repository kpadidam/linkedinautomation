#!/bin/bash

# =================================================================
# LinkedIn Job Automation - Complete Setup Script
# =================================================================
# This script will install everything needed to run the project
# Works on macOS and Linux

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo ""
    echo -e "${GREEN}==========================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}==========================================${NC}"
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="mac"
        print_status "Detected macOS"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        print_status "Detected Linux"
    else
        print_error "Unsupported OS: $OSTYPE"
        exit 1
    fi
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install Homebrew (macOS)
install_homebrew() {
    if ! command_exists brew; then
        print_status "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        # Add Homebrew to PATH for M1/M2 Macs
        if [[ -f "/opt/homebrew/bin/brew" ]]; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
        
        print_success "Homebrew installed"
    else
        print_success "Homebrew already installed"
    fi
}

# Install Python
install_python() {
    print_header "Installing Python"
    
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        print_success "Python3 already installed: $PYTHON_VERSION"
        PYTHON_CMD="python3"
        PIP_CMD="pip3"
    elif command_exists python; then
        PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
        # Check if it's Python 3
        if [[ $PYTHON_VERSION == 3.* ]]; then
            print_success "Python already installed: $PYTHON_VERSION"
            PYTHON_CMD="python"
            PIP_CMD="pip"
        else
            print_warning "Found Python 2, need Python 3"
            PYTHON_CMD=""
        fi
    fi
    
    # Install Python if not found or wrong version
    if [[ -z "$PYTHON_CMD" ]]; then
        if [[ "$OS" == "mac" ]]; then
            print_status "Installing Python 3 via Homebrew..."
            brew install python@3.11
            PYTHON_CMD="python3"
            PIP_CMD="pip3"
        elif [[ "$OS" == "linux" ]]; then
            print_status "Installing Python 3..."
            if command_exists apt-get; then
                sudo apt-get update
                sudo apt-get install -y python3 python3-pip python3-venv
            elif command_exists yum; then
                sudo yum install -y python3 python3-pip
            elif command_exists dnf; then
                sudo dnf install -y python3 python3-pip
            else
                print_error "Unable to install Python. Please install Python 3.8+ manually."
                exit 1
            fi
            PYTHON_CMD="python3"
            PIP_CMD="pip3"
        fi
        print_success "Python 3 installed"
    fi
    
    # Verify pip
    if ! command_exists $PIP_CMD; then
        print_status "Installing pip..."
        if [[ "$OS" == "mac" ]]; then
            brew install python@3.11  # This includes pip
        else
            $PYTHON_CMD -m ensurepip --upgrade
        fi
    fi
    
    print_success "Using Python: $($PYTHON_CMD --version)"
    print_success "Using pip: $($PIP_CMD --version)"
}

# Install Node.js and npm
install_nodejs() {
    print_header "Installing Node.js and npm"
    
    if command_exists node && command_exists npm; then
        NODE_VERSION=$(node --version)
        NPM_VERSION=$(npm --version)
        print_success "Node.js already installed: $NODE_VERSION"
        print_success "npm already installed: $NPM_VERSION"
    else
        if [[ "$OS" == "mac" ]]; then
            print_status "Installing Node.js via Homebrew..."
            brew install node
        elif [[ "$OS" == "linux" ]]; then
            print_status "Installing Node.js..."
            if command_exists apt-get; then
                curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
                sudo apt-get install -y nodejs
            elif command_exists yum; then
                curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
                sudo yum install -y nodejs
            elif command_exists dnf; then
                curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
                sudo dnf install -y nodejs
            fi
        fi
        print_success "Node.js and npm installed"
    fi
}

# Create virtual environment
create_venv() {
    print_header "Creating Python Virtual Environment"
    
    if [[ ! -d "venv" ]]; then
        print_status "Creating virtual environment..."
        $PYTHON_CMD -m venv venv
        print_success "Virtual environment created"
    else
        print_success "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    print_status "Activating virtual environment..."
    source venv/bin/activate
    
    # Upgrade pip in venv
    pip install --upgrade pip
    print_success "Virtual environment activated"
}

# Install Python dependencies
install_python_deps() {
    print_header "Installing Python Dependencies"
    
    if [[ -f "requirements.txt" ]]; then
        print_status "Installing requirements from requirements.txt..."
        pip install -r requirements.txt
        print_success "Python dependencies installed"
    else
        print_error "requirements.txt not found!"
        exit 1
    fi
}

# Install Playwright and browsers
install_playwright() {
    print_header "Installing Playwright Browsers"
    
    print_status "Installing Playwright browsers..."
    playwright install chromium
    
    # Install system dependencies for browsers (Linux)
    if [[ "$OS" == "linux" ]]; then
        print_status "Installing browser system dependencies..."
        playwright install-deps chromium
    fi
    
    print_success "Playwright and Chromium installed"
}

# Setup configuration files
setup_config() {
    print_header "Setting Up Configuration Files"
    
    # Copy .env.example to .env if it doesn't exist
    if [[ ! -f ".env" ]]; then
        if [[ -f ".env.example" ]]; then
            print_status "Creating .env from .env.example..."
            cp .env.example .env
            print_warning "Please edit .env file with your API keys and configuration"
        else
            print_error ".env.example not found!"
        fi
    else
        print_success ".env file already exists"
    fi
    
    # Create credentials.json template if it doesn't exist
    if [[ ! -f "config/credentials.json" ]]; then
        print_status "Creating Google credentials template..."
        mkdir -p config
        cat > config/credentials.json << 'EOF'
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "your-private-key-id", 
  "private_key": "your-private-key",
  "client_email": "your-service-account@your-project.iam.gserviceaccount.com",
  "client_id": "your-client-id",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "your-x509-cert-url",
  "universe_domain": "googleapis.com"
}
EOF
        print_warning "Please replace config/credentials.json with your actual Google Cloud credentials"
    else
        print_success "Google credentials file already exists"
    fi
    
    # Check if resume exists
    if [[ ! -f "resumes/resume.pdf" ]]; then
        print_warning "Please add your resume as 'resumes/resume.pdf'"
        mkdir -p resumes
    else
        print_success "Resume file found"
    fi
}

# Test the setup
test_setup() {
    print_header "Testing Setup"
    
    print_status "Testing Python imports..."
    if python -c "import config; print('✓ Config loads successfully')" 2>/dev/null; then
        print_success "Python configuration test passed"
    else
        print_warning "Python configuration test failed - you may need to configure your .env file"
    fi
    
    print_status "Testing browser installation..."
    if python -c "from playwright.sync_api import sync_playwright; print('✓ Playwright works')" 2>/dev/null; then
        print_success "Playwright test passed"
    else
        print_warning "Playwright test failed"
    fi
    
    print_success "Setup testing complete"
}

# Main installation flow
main() {
    print_header "LinkedIn Job Automation - Complete Setup"
    print_status "This script will install everything needed to run the project"
    
    # Ask for confirmation
    read -p "Do you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Setup cancelled"
        exit 0
    fi
    
    # Detect OS
    detect_os
    
    # Install system dependencies
    if [[ "$OS" == "mac" ]]; then
        install_homebrew
    fi
    
    # Install core components
    install_python
    install_nodejs
    
    # Setup Python environment
    create_venv
    install_python_deps
    install_playwright
    
    # Setup configuration
    setup_config
    
    # Test everything
    test_setup
    
    # Final instructions
    print_header "🎉 Setup Complete!"
    echo ""
    print_success "Everything is installed and ready to go!"
    echo ""
    print_status "Next steps:"
    echo "1. Edit .env file with your API keys"
    echo "2. Replace config/credentials.json with your Google Cloud credentials"
    echo "3. Add your resume as resumes/resume.pdf"
    echo "4. Run the project:"
    echo ""
    echo -e "${GREEN}   source venv/bin/activate${NC}"
    echo -e "${GREEN}   python linkedin.py${NC}"
    echo ""
    print_status "See config/README.md for detailed configuration help"
    echo ""
}

# Run main function
main "$@"
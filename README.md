# Description
This project automates Google Calendar invites based off of a Sling shift scheduling calendar. In order to run this locally, the environment needs to be setup and the Google Calendar API needs to be enabled.

## 🛠️ Installation

### 1. Clone the Repository 
    git clone https://github.com/IsaacTieu/scheduling.git

### 2. Create a Virtual Environment
Create a virtual environment using your preferred tool (e.g., `venv`, `conda`). Here are conda installation instructions.

    cd scheduling
    conda env create -f environment.yml
    conda activate scheduling

## 📥 Enabling Google Calendar API

You will need to set this up if you are using this for the first time.

1. Go to [Google Cloud Console](https://console.cloud.google.com/).

2. Create a new project or use an existing one.

3. Go to APIs & Services > Library, search for Google Calendar API, and enable it.

4. Go to Credentials:
  - Click Create Credentials → OAuth client ID
  - Choose Desktop App
  - Download the .json file

## 📊 Usage

    cd scheduling
    python main.py
    
You will be prompted to fill in a "start" date. This is the first date you want Google Calendar events to populate. For example, if I want to populate Google Calendar events for the week of July 7, 2025, I would type in that date according to the instructions that pop up. Press `enter` after each number is input.

## 📅 Last Updated
This README was last updated on **July 8, 2025**.

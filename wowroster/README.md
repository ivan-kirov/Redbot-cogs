# wowroster - World of Warcraft Roster Management for Redbot

## Introduction

The `wowroster` cog is a plugin for [Redbot](https://github.com/Cog-Creators/Red-DiscordBot) that allows Discord servers to manage and display World of Warcraft character rosters with support for Google Sheets synchronization.

## Features
- Interactive character setup with spec selection
- Google Sheets integration for roster management
- Configurable through Redbot's Config system
- Comprehensive unit tests for key functionality
- Modular architecture for easy extension

## Installation

1. Install Redbot if you haven't already:
   ```bash
   pip install redbot
   ```

2. Clone this repository:
   ```bash
   git clone https://github.com/your-username/Redbot-cogs.git
   ```

3. Navigate to the wowroster directory:
   ```bash
   cd Redbot-cogs/wowroster
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Configure Google Sheets credentials (see Configuration section)

## Configuration

### Google Sheets
1. Create a Google Cloud project and enable the Sheets API
2. Create service account credentials and download the JSON file
3. Set the following in your Redbot config:
   ```yaml
   wowroster:
     google:
       credentials_file: path/to/your-credentials.json
       spreadsheet_id: your-spreadsheet-id
   ```

## Usage

### Commands
- `!setup`: Start the interactive character setup process
- `!sync`: Sync all roster data to Google Sheets
- `!roster`: Display the current roster information

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -am 'Add feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
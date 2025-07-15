# Meeting Room Booking API

This project provides a REST API for booking and querying meeting rooms in the Cathay Holdings booking system.

## Project Overview

This application automates the process of:
1. Querying available meeting rooms for specific dates
2. Booking meeting rooms with specified parameters
3. Extracting and converting meeting room data to CSV format for analysis

## Features

### 1. Meeting Room Query API
- Endpoint: `/run`
- Method: POST
- Functionality: Retrieves meeting room availability information for a specified date
- Returns: CSV data of available meeting rooms

### 2. Meeting Room Booking API
- Endpoint: `/book`
- Method: POST
- Functionality: Books a meeting room with specified parameters
- Returns: JSON response indicating booking status

## Project Structure

```
.
├── booking_meeting_room_api.py   # Main Flask API application
├── output/                       # Output directory for CSV and text data
│   └── YYYYMMDD_combined.csv     # CSV outputs of meeting room data
├── tmp/                          # Temporary files used during processing
└── utils/                        # Utility scripts and helpers
    ├── 2_html_filter.sh          # Shell script for filtering HTML data
    └── convert_to_csv.py         # Python utility for CSV conversion
```

## Technical Details

### Dependencies
- Flask: Web framework for API endpoints
- Selenium: Browser automation for interacting with the booking system
- Python standard libraries: csv, os, time, subprocess

### How It Works

#### Meeting Room Query Process:
1. Authenticates with the booking system
2. Navigates to the meeting room search page
3. Sets the search parameters (date, building)
4. Retrieves morning and afternoon availability data
5. Processes the HTML data using shell scripts
6. Converts the data to structured CSV format
7. Returns the data to the API caller

#### Meeting Room Booking Process:
1. Authenticates with the booking system
2. Navigates to the booking interface
3. Selects the specified meeting room
4. Fills in meeting details (subject, time, attendees)
5. Submits the booking request
6. Returns a success/failure response

## Usage

### Querying Meeting Rooms
```bash
curl -X POST http://localhost:5000/run \
  -H "Content-Type: application/json" \
  -d '{"date": "2024/09/20"}'
```

### Booking a Meeting Room
```bash
curl -X POST http://localhost:5000/book \
  -H "Content-Type: application/json" \
  -d '{
    "room_number": "3303",
    "start_date": "2025/07/16",
    "meeting_subject": "Technical Discussion",
    "time_from": "08:00",
    "time_to": "09:00"
  }'
```

## Setup Instructions

1. Clone the repository
2. Install the required dependencies:
   ```bash
   pip install flask selenium
   ```
3. Ensure Chrome WebDriver is installed and available in your PATH
4. Run the API server:
   ```bash
   python booking_meeting_room_api.py
   ```
5. The API will be available at http://localhost:5000

## Output Data Format

The CSV output contains the following columns:
- 會議室 (Meeting Room)
- 會議時間 (Meeting Time)
- 會議名稱 (Meeting Name)
- 借用人 (Requester)

## Security Notes

- Credentials should be stored securely and not hardcoded in the application
- Consider implementing proper authentication for the API endpoints

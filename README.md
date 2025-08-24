## AI Travel Agent
Create a low budget and cost affordable travel itinerary with detialed information that syncs directly to your Google Calendar. Best for vacations less than 2 weeks. It locally hosts a webpage for the user to input all the necessary information about the trip to then create the optimal trip. 

## Overview
This AI travel agent powered by Arcade and Anthropic: 

1. Locally hosts a webpage
2. Retrieves all the data the user inputs
3. Uses Anthropic to generate an itinerary
4. Arcade sends you an email with the itinerary
5. Arcade links it directly into your Google Calendar
6. Enjoy a wonderful trip!

## Features
- 🗺️ Custom travel itineraries using Claude AI
- ✈️ Flight and driving trip options  
- 📧 Email delivery of complete itineraries
- 📅 Automatic calendar event creation
- 🏨 Hotel and restaurant recommendations
- 🚗 Gas/charging station suggestions for road trips
- 💰 Has price estimates

## Necessary APIs
First, go to Arcade.dev (https://arcade.dev) to set up an account and generate an API key to grant authorization to the tools with Gmail and Google Calendar. 
Then, generate an Anthropic API key (https://docs.anthropic.com/en/api/admin-api/apikeys/get-api-key)

# API Keys Setup Guide

## Arcade API Key
1. Visit [[Arcade.dev](https://arcade.dev)]
2. Sign up for an account
3. Navigate to API Keys section
4. Generate a new key

## Anthropic API Key
1. Go to [[Anthropic Console](https://docs.anthropic.com/en/api/admin-api/apikeys/get-api-key)]
2. Create account and billing setup
3. Generate API key

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ai-travel-agent.git
   cd ai-travel-agent


   ```

2. **Install required packages**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file in the project root with the following variables:
   ```
   # API Keys
   ARCADE_API_KEY=your_arcade_api_key
   ANTHROPIC_API_KEY=your_anthropic_api_key
   
   ```

4. **Run the application**
   ```bash
   python main.py
   ```

5. **Open on Flask**
  Open on any brower http://localhost:2800/ to plan your journey!

   For the first run, you'll need to authorize the application with Google through the Arcade.dev API. The link will be provided in the terminal.


## Contributing

Fork the repository
Create a feature branch (git checkout -b feature/amazing-feature)
Commit your changes (git commit -m 'Add amazing feature')
Push to the branch (git push origin feature/amazing-feature)
Open a Pull Request

## License
This project is licensed under the MIT License - see the LICENSE file for details.


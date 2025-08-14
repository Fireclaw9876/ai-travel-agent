from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import sys
from openai import OpenAI
from datetime import datetime 
from email_validator import validate_email, EmailNotValidError
import anthropic
import traceback
from pathlib import Path
from arcadepy import Arcade
from dotenv import load_dotenv, find_dotenv

# Make a trip class to hold trip information
class trip:
    def __init__(self, start_location, travel_location, passenger_adult_count, passenger_child_count, travel_class, arrival_date, departure_date, travel_preferences):
        self.start_location = start_location
        self.travel_location = travel_location
        self.passenger_adult_count = passenger_adult_count
        self.passenger_child_count = passenger_child_count
        self.travel_class = travel_class
        self.arrival_date = arrival_date
        self.departure_date = departure_date
        self.travel_preferences = travel_preferences

# Initialize global variables
trip_info = None
client = None
anthropic_client = None
USER_ID = None

# Load API key from encrypted .env file
def get_api_keys():
    try:
        print("Loading environment variables...")
        env_path = find_dotenv()
        if not env_path:
            raise FileNotFoundError(".env file not found. Please ensure it exists in the project root directory.")
        load_dotenv(dotenv_path=Path(env_path))
        # Fetch API keys from environment variables
        arcade_api_key = os.getenv("ARCADE_API_KEY")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        serp_api_key = os.getenv("SERP_API_KEY")
        # Check if the API keys are not None or empty
        if not arcade_api_key or not openai_api_key or not anthropic_api_key or not serp_api_key:
            raise ValueError("One or more API keys are missing. Please check your .env file.")
        print("Environment variables loaded successfully.")
        return arcade_api_key, openai_api_key, anthropic_api_key, serp_api_key
    except Exception as e:
        print(f"Error loading environment variables: {e}")
        traceback.print_exc()
        sys.exit(1) 

def get_anthropic_plan(trip):
    # Validate input information
    if not all([trip.start_location, trip.travel_location, trip.arrival_date, trip.departure_date]):
        raise ValueError("Missing required trip information")
    print("Validated trip information successfully.")
    # Define the tool for structured output
    tools = [{
        "name": "travel_events",
        "description": "A comprehensive list of events for the trip itinerary.",
        # Define the input schema for the tool
        "input_schema": {
            "type": "object",
            "properties": {
                "events": {
                    # For multiple events, use an array of objects
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            # Specify the properties for each event
                            "event_name": {"type": "string"},
                            "event_time": {"type": "string"},
                            "event_price": {"type": "string"},
                            "event_address": {"type": "string"},
                            "event_description": {"type": "string"},
                        },
                        # Required properties for each event
                        "required": ["event_name", "event_address", "event_time"],
                        "additionalProperties": False,
                    }
                }
            },
            "required": ["events"],
            "additionalProperties": False,
        }
    }]
    print("Tool schema defined successfully.")
    
    # Prompt for the Anthropic API
    prompt = f"""Generate a travel itinerary from {trip.start_location} to {trip.travel_location} for {trip.passenger_adult_count} adults and {trip.passenger_child_count} children between the dates of {trip.arrival_date} and {trip.departure_date}
        Center the itinerary around their travel preferences as stated below: {trip.travel_preferences}
             
        First, think carefully step by step about what documents are needed to answer the query. If you are not sure about the information that you have, use your tools to read files and gather the relevant information. Do NOT guess or make up an answer.
        If there's not enough information about the location to create a detailed itinerary, please explain why you cannot provide a complete answer.
            
        Then please provide the following details for each event:
            1. Event Name: Add relevant emojis and brief descriptions for obscure venues (e.g., "MET (Metropolitan Museum of Art)")
            2. Event Time: Specific date/time in ISO 8601 format, or explain if unknown
            3. Event Price: Specific costs or explain if prices vary/unknown
            4. Event Address: Complete address or explain if location varies/unknown  
            5. Event Description: A detailed paragraph covering the event's significance, including reviews, cultural context, historical importance, or pop culture references

        These events MUST include: flights, hotels, activities, and restaurants for all three meals. Hotel location and flight times should be included in the itinerary. Affordable and delicious restaurants should be included in the itinerary with their addresses and hours of operation. I would also recommend parks, districts, and other places of interest that are not tourist traps.
        Unless otherwise specified, the events should be in chronological order. There should at least be 3 events per day not including dinner, breakfast, and lunch. 
        Search for bakeries, cafes, and restaurants to eat that are not tourist traps.
        If there are any special events or festivals happening during the trip, include those as well.
        
        For the flights, include the IATA codes for the airports and format it this way: "Flight: SFO to JFK" for a flight from San Francisco to New York.
        Focus on creating a balanced itinerary that matches their stated preferences while including practical information like addresses and timing.
       
        Please use the travel_events tool to structure your response with the itinerary data.
        """
    # Ensure responses adhere to JSON format
    try:
        print("Generating travel plan using Anthropic API...")
        # Make the API call to Claude
        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            temperature=0.7,
            system="You are an expert travel planner with years of experience creating unforgettable trips. You specialize in comprehensive, detailed itineraries that include practical information like dates, locations, and costs. Always use the provided tool to structure your response with well-organized itinerary data.",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            tools=tools,
            tool_choice={"type": "tool", "name": "travel_events"}
        )
        print("Anthropic API call completed successfully.")
        # Parse Response to return a dictionary
        if response.content: 
            # Check if the response contains tool calls and valid arguments
            for content_block in response.content:
                if content_block.type == "tool_use" and content_block.name == "travel_events":
                    itinerary_data = content_block.input
                    print("Itinerary data extracted successfully.")
                    return {
                        "itinerary": itinerary_data["events"],
                        "event_count": len(itinerary_data["events"]),
                        "model_used": "claude-3-5-sonnet-20241022"
                    }
            print("No valid tool use found in the response.")
            # If no tool use found, return text content if available
            text_content = ""
            for content_block in response.content:
                if content_block.type == "text":
                    text_content += content_block.text
            print("Text content from response:", text_content)
            return None
    # Handle any exceptions that occur during the API call
    except Exception as e:
        print(f"Error in Anthropic API call: {e}")
        traceback.print_exc()
        return None

# Use Arcade to Access Booking for Flights and Hotels
def get_flight_booking(client, trip, result):
    # Parse through Content to get flight details
    print("Extracting flight details from the itinerary...")
    flight_details = []
    
    # Pass and format data for Arcade
    for event in result["itinerary"]:
        if "flight" in event["event_name"].lower():
            # Extract Airport Location
            if "to" in event["event_name"].lower():
                start_airport = event["event_name"].split(" to ")[0].split(": ")[1].strip()
                end_airport = event["event_name"].split(" to ")[1].strip()
            else:
                raise ValueError("Flight event name does not contain 'to' for start and end airports.")
            # Validate Airport Codes
            print(f"Start Airport: {start_airport}, End Airport: {end_airport}")
            if len(start_airport) != 3 or len(end_airport) != 3:
                raise ValueError("Airport codes must be 3 characters long (IATA codes).")
            # Change Event Time to Date (Year-Month-Day)
            event["event_time"] = event["event_time"].split("T")[0] if "T" in event["event_time"] else event["event_time"]
            # Extract flight details from the event
            flight_details.append({
                "start_airport": start_airport,
                "end_airport": end_airport,
                "time": event["event_time"],
                "price": event["event_price"],
                "address": event["event_address"],
                "description": event["event_description"]
            })
                
    # Use Arcade to book the flight
    if flight_details:
        print("Booking flight using Arcade...")
        arcade_tool_name = "Search.SearchOneWayFlights"
        tool_input = {
            "departure_airport_code": flight_details[0]["start_airport"],
            "arrival_airport_code": flight_details[0]["end_airport"],
            "outbound_date": flight_details[0]["time"],
            "currency_code": "USD",
            "travel_class": "ECONOMY",
            "num_adults": trip.passenger_adult_count,
            "num_children": trip.passenger_child_count,
            "max_stops": "ANY",
            "sort_by": "PRICE",
        }
        
        response = client.tools.execute(
        tool_name=arcade_tool_name,
        input=tool_input,
        user_id=USER_ID,)   
        return response
    else:
        return ValueError("No flight details found in the itinerary.")

def sendEmail(trip, result):
    try:
        print("Sending email with trip details...")
        # Request access to the user's Gmail account
        auth_response = client.tools.authorize(
        tool_name="Gmail.SendEmail",
        user_id=USER_ID,
        ) 
        
        email_content = get_email_content(trip, result)
        
        tool_input = {
            "subject" : "Your Upcoming Trip to " + trip.travel_location, 
            "body" : email_content,
            "recipient": USER_ID,
        }
        
        emails_response = client.tools.execute(
            tool_name="Gmail.SendEmail",
            input=tool_input,
            user_id=USER_ID,
        )
        print("Email sent successfully")
    except ValueError as ve:
        print(f"ValueError: {ve}")
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"Error sending email: {e}")
        traceback.print_exc()
        return None
    
def get_email_content(trip, result):
    try:
        print("Generating email content...")
        # Create the email content
        email_content = f"""
        Hi,

        Here is your travel itinerary for your upcoming trip from {trip.start_location} to {trip.travel_location}.
        
        Trip Details:
        - Arrival Date: {trip.arrival_date}
        - Departure Date: {trip.departure_date}
        - Travel Preferences: {trip.travel_preferences}

        
        Itinerary:
        """
        # Initalize Dictionary for event details
        event_details = []
        # Populate event details with result from the API call
        for event in result["itinerary"]:
            event_details.append({
                "name": event["event_name"],
                "time": event["event_time"],
                "price": event["event_price"],
                "address": event["event_address"],
                "description": event["event_description"]
            })

        # Format the event details into the email content
        for i, event in enumerate(event_details, start=1):
            email_content += f"""
            Event {i}:
            - Name: {event['name']}
            - Time: {event['time']}
            - Price: {event['price']}
            - Address: {event['address']}
            - Description: {event['description']}
            """
        
        email_content += "\n\nSafe travels!\n"
        
        print("Email content generated successfully.")
        return email_content
    except Exception as e:
        raise ValueError(f"Error generating email content: {e}")
        
def add_calendar_event(client, event):
    try:
        # Call Arcade to add a calendar event
        TOOL_NAME = "GoogleCalendar.CreateEvent"
        auth_response = client.tools.authorize(
        tool_name=TOOL_NAME,
        user_id=USER_ID,
        )

        if auth_response.status != "completed":
            print(f"Click this link to authorize: {auth_response.url}")

        # Wait for the authorization to complete
        client.auth.wait_for_completion(auth_response)
        print("Calendar authorization completed successfully.")
        # Prepare the tool input for the calendar event
        tool_input = {
            "summary": event["event_name"],
            "description": event["event_description"],
            "start_datetime": event["event_time"],
            "end_datetime": event["event_time"],  # Adjust as needed
            "location": event["event_address"],
            "attendees": [USER_ID],
            "calendar_id": "primary",
        }
        client.tools.execute(
            tool_name=TOOL_NAME,
            input=tool_input,
            user_id=USER_ID,
        )
    except Exception as e:
        print(f"Error adding calendar event: {e}")
        traceback.print_exc()
        return None

# Call the function to test
if __name__ == "__main__":
    # Initialize Trip Details
    test_trip = trip(
        # MUST BE FROM CITY TO CITY
        "Houston",
        "San Francisco",
        1,
        0,
        "Economy",
        "2025-08-10",
        "2025-08-12",
        "I want to go shopping and see the museums."
    )
    # Get API keys
    arcade_api_key, openai_api_key, anthropic_api_key, serp_api_key = get_api_keys()
    # Initialize Arcade client
    client = Arcade() # Automatically finds the `ARCADE_API_KEY` env variable
    # Pass a unique identifier for them (e.g. an email or user ID) to Arcade:
    USER_ID = "kailichu14@gmail.com"
    # Initialize Anthropic client
    anthropic_client = anthropic.Client(
        api_key=anthropic_api_key
    )
    # Send Email to User
    print("Starting the trip planning process...")
    send_initial_email()
    
    # Get the travel plan
    result = get_anthropic_plan(test_trip)
    
    # Send the email with trip details
    sendEmail(trip=test_trip, result=result)
    # Add a Calendar Event
    for event in result["itinerary"]:
        add_calendar_event(client, event)
    
    print("Trip planning process completed successfully.")

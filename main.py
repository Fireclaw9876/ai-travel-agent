# Import all necessary libraries
from flask import Flask, render_template, request, redirect, url_for, flash
import os
import sys
from openai import OpenAI
from datetime import datetime, timedelta 
import json
from email_validator import validate_email, EmailNotValidError
import anthropic
import traceback
from pathlib import Path
from arcadepy import Arcade
from dotenv import load_dotenv, find_dotenv

class trip:
    """ 
    Represents a travel booking with passenger details and preferences. 
    Stores all necessary information to curate the travel plan. 
    """
    def __init__(self, user_email, start_location, travel_location, passenger_adult_count, passenger_child_count, travel_style, car_type, travel_class, arrival_date, departure_date, travel_preferences):
        self.user_email = user_email
        self.start_location = start_location
        self.travel_location = travel_location
        self.passenger_adult_count = passenger_adult_count
        self.passenger_child_count = passenger_child_count
        self.travel_style = travel_style
        self.car_type = car_type
        self.travel_class = travel_class
        self.arrival_date = arrival_date
        self.departure_date = departure_date
        self.travel_preferences = travel_preferences

# Initialize constants
MY_TRIP = None
anthropic_client = None
USER_ID = None

# Load API key from encrypted .env file
def get_api_keys():
    global arcade_api_key, openai_api_key, anthropic_api_key
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
        # Check if the API keys are not None or empty
        if not arcade_api_key or not openai_api_key or not anthropic_api_key:
            raise ValueError("One or more API keys are missing. Please check your .env file.")
        print("Environment variables loaded successfully.")
        return arcade_api_key, anthropic_api_key
    except Exception as e:
        print(f"Error loading environment variables: {e}")
        traceback.print_exc()
        sys.exit(1) 

# Construct Flask app for user interface
app = Flask(__name__, template_folder='templates')
app.secret_key = os.getenv("SECRET_KEY", "bpSOP_\xc5r\xa2H\x15\xaa\x12\r8]\xb1\x02\x15\xfe\xfd\x9d\xf9\xf0\xdb\xcek")

# Make sure templates exist
template_path = os.path.join('templates', 'welcome.html')
print(f"Template path: {template_path}")
print(f"Template exists: {os.path.exists(template_path)}")

# Get API Keys
arcade_api_key, anthropic_api_key = get_api_keys()

# Rendering the template for the Flask homepage
@app.route('/')
def home():
    return render_template('welcome.html')

# UI to process trip information
@app.route('/planner', methods=['POST', 'GET'])
def base():
    global MY_TRIP
    if request.method == 'POST':
        try:
            # Get all form data first
            user_email = request.form.get('user_email')
            start_location = request.form.get('start_location')
            travel_location = request.form.get('travel_location')
            arrival_date_str = request.form.get('arrival_date')
            departure_date_str = request.form.get('departure_date')
            travel_style = request.form.get('travel_style')
            car_type = request.form.get('car_type')
            travel_class = request.form.get('travel_class')
            travel_preferences = request.form.get('travel_preferences')
            
            # Required Fields
            required_fields = [
                'user_email', 'start_location', 'travel_location', 
                'arrival_date', 'departure_date'
            ]

            # Validate email
            if not user_email:
                flash("Email is required")
                return render_template('planner.html')
            validate_email(user_email)
            
            # Validating that the cities exist
            if not validate_cities(start_location, travel_location):
                flash("Please check that your location inputs are cities, and spelled correctly. If it still does not work, try different iterations of the city name.")
                return render_template('planner.html')
            # Validate required fields
            for field in required_fields:
                if not request.form.get(field):
                    flash(f"{field.replace('_', ' ').capitalize()} is required")
                    return render_template('planner.html')
            
            # Validate passenger counts
            passenger_adult_count = int(request.form.get('passenger_adult_count', 0))
            passenger_child_count = int(request.form.get('passenger_child_count', 0))
            
            if passenger_adult_count < 1:
                flash("At least one adult passenger is required")
                return render_template('planner.html')
            if passenger_child_count < 0:  # Children can be 0, but not negative
                flash("Child count cannot be negative")
                return render_template('planner.html')
            
            # Validate dates
            arrival_date = datetime.strptime(arrival_date_str, '%Y-%m-%d').date()
            departure_date = datetime.strptime(departure_date_str, '%Y-%m-%d').date()
            
            # Ensuring logical arrival date before departure date 
            if arrival_date >= departure_date:
                flash("Arrival date must be before departure date")
                return render_template('planner.html')
            
            # Limit the time frame for the trip to 2 weeks
                # Don't want to overwhelm and overuse AI (considerations on budget and run-time)
            if (departure_date - arrival_date) > timedelta(days=14):
                flash("Stay cannot exceed 14 days")
                return render_template('planner.html')

            # Ensure the dates are valid -- travel dates must be in the present or future 
            if arrival_date < datetime.now().date():
                flash("Arrival date cannot be in the past")
                return render_template('planner.html')
            
            # Check for empty scenario
            if not travel_preferences:
                travel_preferences = None

            # Pass validation information  
            MY_TRIP = trip(
                user_email,
                start_location, 
                travel_location, 
                passenger_adult_count, 
                passenger_child_count, 
                travel_style,
                car_type,
                travel_class, 
                arrival_date, 
                departure_date, 
                travel_preferences
            )

            # Process the trip information
            return redirect(url_for('loading'))
        except EmailNotValidError as e: 
            flash("Invalid email address format", 'error')
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash("An unexpected error occurred. Please try again.", 'error')
            # Log the actual error for debugging
            print(f"Unexpected error in base route: {e}")
        #  Error handling - render form again
        return render_template('planner.html')
    # GET request - show the form
    return render_template('planner.html')

@app.route('/loading')
def loading():
    # Ensure the object data is correctly stored
    if not MY_TRIP: 
        print('No Trip Validated')
        return redirect(url_for('planner')) # Redirect back to planner if necessary
    # Proceed to loading page
    return render_template('loading.html')

@app.route('/backend_processing')
def backend_processing():
    """
    This function executes all the backend which includes calling Anthropic's API and using Arcade to authorize the user's email and Google Calendar. 
    It then conducts multiple tool executions
    """
    process_backend()
    return redirect(url_for('submitted')) # Redirects to the submitted page once finished processing

@app.route('/submitted')
def submitted():
    try:
        # Showing all important trip information in terminal
        print("trip info: ", MY_TRIP)
        print(f"Trip details: {MY_TRIP.user_email}, {MY_TRIP.start_location} -> {MY_TRIP.travel_location}")
        print(f"Dates: {MY_TRIP.arrival_date} to {MY_TRIP.departure_date}")
        print(f"Passengers: {MY_TRIP.passenger_adult_count} adults, {MY_TRIP.passenger_child_count} children")

        return render_template('submitted.html')
    except Exception as e:
        print(f"Error processing trip: {e}")
        print(f"Error type: {type(e)}")
        traceback.print_exc()
        flash("An error occurred while processing your trip.", 'error')
        return redirect(url_for('home'))

# 404 Error Handler
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

# 500 Error Handler
@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

def process_backend():
    global client, MY_TRIP, anthropic_client, USER_ID
    try:
        client = Arcade() # Automatically finds the `ARCADE_API_KEY` env variable
        print("Arcade client initialized successfully")
        
        # Pass a unique identifier for them (e.g. an email or user ID) to Arcade:
        USER_ID = MY_TRIP.user_email
        print(f"User ID set to: {USER_ID}")

        # Initialize Anthropic client
        anthropic_client = anthropic.Client(
            api_key=anthropic_api_key
        )
        print("Anthropic client initialized successfully")
        
        print("Starting the trip planning process...")

        # Get the travel plan
        print("Calling get_anthropic_plan...")
        result = get_anthropic_plan(MY_TRIP)
        print(f"get_anthropic_plan returned: {type(result)}")
        
        # Show some event names on the Terminal
        if result:
            print(f"Generated itinerary with {result['event_count']} events")
            print("First few events:")
            for i, event in enumerate(result["itinerary"][:3]):
                print(f"  Event {i+1}: {event.get('event_name', 'No name')}") 
            # Send the email with trip details
            send_email(trip=MY_TRIP, result=result)
            # Add a Calendar Event
            for event in result["itinerary"]:
                add_calendar_event(client, event)
            print("Calendar events added successfully.")
    except Exception as e:
        print(f"Error processing trip: {e}")
        print(f"Error type: {type(e)}")
        traceback.print_exc()

def get_anthropic_plan(trip):
    # Validate input information
    if not all([trip.start_location, trip.travel_location, trip.arrival_date, trip.departure_date]):
        raise ValueError("Missing required trip information")
    print("Validated trip information successfully.")
    # Define the tool for structured output
    tools = [{
        "name": "travel_events",
        "description": "A comprehensive list of events for the trip itinerary.",
        "input_schema": {
            "type": "object",
            "properties": {
                "events": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "event_name": {"type": "string"},
                            "event_time": {"type": "string"},
                            "event_price": {"type": "string"},
                            "event_address": {"type": "string"},
                            "event_description": {"type": "string"}
                        },
                        "required": ["event_name", "event_address", "event_time"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["events"],
            "additionalProperties": False
        }
    }]

    print("Tool schema defined successfully.")
    
    # Prompt specific to the Flight Travel Style (includes airport codes, plane times, etc.)
    prompt_flight = f"""Generate a travel itinerary from {trip.start_location} to {trip.travel_location} for {trip.passenger_adult_count} adults and {trip.passenger_child_count} children between the dates of {trip.arrival_date} and {trip.departure_date}
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

    # Prompt specific to the Driving Travel Style (includes gas stations or electrical vehicle charging stations)
    prompt_road_trip = f"""Generate a road-trip style travel itinerary from {trip.start_location} to {trip.travel_location} for {trip.passenger_adult_count} adults and {trip.passenger_child_count} children between the dates of {trip.arrival_date} and {trip.departure_date}
        Center the itinerary around their travel preferences as stated below: {trip.travel_preferences}
             
        First, think carefully step by step about what documents are needed to answer the query. If you are not sure about the information that you have, use your tools to read files and gather the relevant information. Do NOT guess or make up an answer.
        If there's not enough information about the location to create a detailed itinerary, please explain why you cannot provide a complete answer.
            
        Then please provide the following details for each event:
            1. Event Name: Add relevant emojis and brief descriptions for obscure venues (e.g., "MET (Metropolitan Museum of Art)")
            2. Event Time: Specific date/time in ISO 8601 format, or explain if unknown
            3. Event Price: Specific costs or explain if prices vary/unknown
            4. Event Address: Complete address or explain if location varies/unknown  
            5. Event Description: A detailed paragraph covering the event's significance, including reviews, cultural context, historical importance, or pop culture references

        These events MUST include: hotels, activities, and restaurants for all three meals. Affordable and delicious restaurants should be included in the itinerary with their addresses and hours of operation. I would also recommend parks, districts, and other places of interest that are not tourist traps.
        Unless otherwise specified, the events should be in chronological order. There should at least be 3 events per day not including dinner, breakfast, and lunch. 
        Search for bakeries, cafes, and restaurants to eat that are not tourist traps.
        If there are any special events or festivals happening during the trip, include those as well.
        
        Attempt to include vehicle renewal stations (ie. gas stations or electrical vehicle charging stations for the user). This person prefers {trip.car_type} cars so add some of these renewal stations based on their mileage. 
        For a gas car, include a gas station every 400 miles or so. For an electric car, include a charging station every 200 miles or so. If there are no gas stations, add an event that is a warning for that information. 
        
        Focus on creating a balanced itinerary that matches their stated preferences while including practical information like addresses and timing.
       
        Please use the travel_events tool to structure your response with the itinerary data.
        """
    # Ensure responses adhere to JSON format
    try:
        # Specific prompts for each option 
        if trip.travel_style == "Flying":
            prompt = prompt_flight
        elif trip.travel_style == "Driving":
            prompt = prompt_road_trip
        # Default fallback option
        else:
            prompt = prompt_flight 

        print("Generating travel plan using Anthropic API...")

        # Make the API call to Claude
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            temperature=0.7,
            # Providing more background for the LLM
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
        # Check type
        print(f"Response type: {type(response)}")
        print(f"Response content: {response.content}")

        # Parse Response to return a dictionary
        if response.content: 
            # Check if the response contains tool calls and valid arguments
            for content_block in response.content:
                if content_block.type == "tool_use" and content_block.name == "travel_events":
                    itinerary_data = content_block.input
                    print("Itinerary data extracted successfully.")

                    # Handle different possible response structures
                    events = None
                    if "events" in itinerary_data:
                        events = itinerary_data["events"]
                    elif "itinerary" in itinerary_data:
                        events = itinerary_data["itinerary"]
                    else:
                        # If neither key exists, try to use the whole data as events
                        print("Warning: Expected 'events' key not found in response")
                        print(f"Available keys: {list(itinerary_data.keys())}")
                        # Try to find any array-like structure
                        for key, value in itinerary_data.items():
                            if isinstance(value, list):
                                events = value
                                print(f"Using '{key}' as events array")
                                break
    
                    return {
                        "itinerary": itinerary_data["events"],
                        "event_count": len(itinerary_data["events"]),
                        "model_used": "claude-sonnet-4-20250514"
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

def send_email(trip, result):
    try:
        print("Sending email with trip details...")
        # Request access to the user's Gmail account
        auth_response = client.tools.authorize(
        tool_name="Gmail.SendEmail",
        user_id=USER_ID,
        ) 

        if auth_response.status != "completed":
            print(f"Click this link to authorize: {auth_response.url}")

        # Wait for authorization
        client.auth.wait_for_completion(auth_response)
        print("Email authorization completed successfully.")
        
        email_content = get_email_content(trip, result)

        # Inputs for the tool 
        tool_input = {
            "subject" : "Your Upcoming Trip to " + trip.travel_location, 
            "body" : email_content,
            "recipient": USER_ID,
        }
        
        # Executing the tool
        emails_response = client.tools.execute(
            tool_name="Gmail.SendEmail",
            input=tool_input,
            user_id=USER_ID,
        )
        print("Email sent successfully:", emails_response.output.value)
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

def validate_cities(from_city, to_city):
    try:
        # Standardized to lowercase format 
        from_city, to_city = from_city.lower(), to_city.lower()
        # Parse the json file filled with all city names
        with open('cities.json', 'r') as file:
            data = json.load(file)
            city_names = []
            # Extract all city names into an array
            for city in data:
                name = city.get('name').lower()
                city_names.append(name)
        # Validating the existence of these cities
        if from_city in city_names and to_city in city_names:
            print("Valid cities")
            return True
        else:
            print("Invalid cities -> returning error")
            return False
    except FileNotFoundError:
        print("Error: THe file 'data.json' was not found.")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from file: {e}")
    except Exception as e:
        print(f"Unexpected error occured: {e}")
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Set up Flask
    app.run(debug=True, host="0.0.0.0", port=2800)

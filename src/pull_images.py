# Helper functions to pull player profile images which can be used when displaying MVP predictions

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import csv, os
from PIL import Image
from io import BytesIO

current_dir = os.getcwd()
parent_dir = os.path.dirname(current_dir)

# This function is intended to be invoked interactively from the /nbamvp/src directory.
#
# This function pulls profile images from a hardcoded image URL prefix. It's unwise to assume this prefix
# will work in all seasons or for all players.
#
# To update player slugs & images in the future, run these python commands interactively:
# First, check whether you want to delete the previous images first (might not be necessary)
# > import generate_data as gd
# > import pull_images as pi
# > gd.pull_slugs(2024)
# > pi.pull_img_url("../data/player_slugs.csv")
def pull_img_url(slug_filepath):
    # An image url looks like this: "https://www.basketball-reference.com/req/202106291/images/headshots/butleji01.jpg"
    img_url_prefix = "https://www.basketball-reference.com/req/202106291/images/headshots/"
    img_url_postfix = ".jpg"

    # Open the slug file
    # Typically, the slug_filepath should be = "data/player_slugs.csv"
    reader = csv.reader(open(slug_filepath, 'r'))

    # Get a list of slugs
    slugs = [row[0] for row in reader]

    # For each slug in list:
    for slug in slugs:
        # Generate the image URL
        img_url = img_url_prefix + slug + img_url_postfix

        # Pull the image
        image_response = requests.get(img_url)
        
        # Check if the request for the image was successful
        if image_response.status_code == 200:
            # Format & save it
            format_and_save_image(slug, image_response.content)
        else:
            # Be sure to report any errors
            print("Failed to download image.")
            print(">   Player Slug: " + slug)
            print(">   Image URL: " + img_url)


# This function is intended to be invoked interactively from the /nbamvp/src directory.
#
# This function pulls profile images by scraping the player profile pages to dynamically access the profile
# image URLs. It's a bit more robust than the previous function, but it does assume a profile URL prefix
# for each player.
def scrape_profile(slug_filepath):
    # A profile url looks like this: "https://www.basketball-reference.com/players/b/butleji01.html"
    # Note that the /b/ before butleji01 is the first character of the player slug.
    profile_url_prefix = "https://www.basketball-reference.com/players/"
    profile_url_postfix = ".html"

    # Open the slug file
    # Typically, the slug_filepath should be = "data/player_slugs.csv"
    reader = csv.reader(open(slug_filepath, 'r'))

    # Get a list of slugs
    slugs = [row[0] for row in reader]

    # For each slug in list:
    for slug in slugs:
        # Generate the profile URL
        slug_prefix = slug[0] + '/'
        prof_url = profile_url_prefix + slug_prefix + slug + profile_url_postfix

        # Access the profile
        response = requests.get(prof_url)

        # Navigate to the image URL
        if response.status_code == 200:
            # Parse the HTML content of the page
            soup = BeautifulSoup(response.content, 'html.parser')

            # Navigate to the specific HTML elements containing the image URL
            image_element = soup.find('div', {'class': 'media-item'}).find('img')

            # Get the source (src) attribute of the image element
            image_url = image_element['src']

            # Join the absolute URL if it's a relative path
            image_url = urljoin(prof_url, image_url)

            # Pull the image
            # Send a GET request to the image URL
            image_response = requests.get(image_url)

            # Check if the request for the image was successful
            if image_response.status_code == 200:
                # Format & save it
                format_and_save_image(slug, image_response.content)
            else:
                # Be sure to report any errors
                print("Failed to download image.")
                print(">   Player Slug: " + slug)
                print(">   Profile URL: " + prof_url)
                print(">   Image URL: " + image_url)
        else:
            print("Failed to scrape the webpage. Status code:", response.status_code)
            print(">   Player Slug: " + slug)
            print(">   Profile URL: " + prof_url)


# Helper function
def format_and_save_image(slug, image_content):
    # Create file name & path
    img_name = slug + ".jpg"
    img_filepath = '../data/player_images/' + img_name
    # img_filepath = '../data/player_img_test2/' + img_name

    # Crop the image down
    image_data = BytesIO(image_content)
    img = Image.open(image_data)
    crop_box = (10, 0, 110, 140)
    img = img.crop(crop_box)

    # Resizing: Calculate new size based on percentage
    resize_percentage = 60
    original_width, original_height = img.size
    new_width = int(original_width * (resize_percentage / 100))
    new_height = int(original_height * (resize_percentage / 100))

    # Resizing: Finish the job
    img = img.resize((new_width, new_height), resample=Image.Resampling.LANCZOS)

    # Save it
    img.save(img_filepath)
    print("Image downloaded successfully.")
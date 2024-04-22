from flask import Flask, render_template, request
from bs4 import BeautifulSoup
import requests
from flask_mysqldb import MySQL
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

app = Flask(__name__)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root@123'
app.config['MYSQL_DB'] = 'price_comparison'

mysql = MySQL(app)


def scrape_amazon_products(query):
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Ensure GUI is off
    driver = webdriver.Chrome(options=chrome_options)

    url = f'https://www.amazon.in/s?k={query}'
    driver.get(url)
    time.sleep(5)  # Allow time for the page to fully load

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    products = []

    while True:
        search_results = soup.find_all(attrs={"data-component-type": "s-search-result"})

        for result in search_results:
            product_name = result.find('span', {'class': 'a-text-normal'}).text.strip()
            try:
                product_price = result.find('span', {'class': 'a-offscreen'}).text.strip()
            except AttributeError:
                product_price = "Price not available"
            try:
                availability = result.find('span', {'class': 'a-size-base'}).text.strip()
            except AttributeError:
                availability = "Availability not available"
            product_link = result.find('a', {'class': 'a-link-normal'})['href']
            product_link = f"https://www.amazon.in{product_link}"
            # Extracting image URL
            img_tag = result.find('img', {'class': 's-image'})
            if img_tag:
                img_url = img_tag['src']
                products.append({
                    "name": product_name,
                    "price": product_price,
                    "availability": availability,
                    "link": product_link,
                    "image": img_url
                })

        # Check if there's a next page
        next_page = soup.find('li', {'class': 'a-last'})
        if not next_page:
            break

        # Click on next page using Selenium
        next_page_link = next_page.find('a')['href']
        driver.get(f"https://www.amazon.in{next_page_link}")
        time.sleep(5)  # Allow time for the next page to load
        soup = BeautifulSoup(driver.page_source, 'html.parser')

    driver.quit()
    return products


def scrape_flipkart_products(query):
    products = []
    url = f"https://www.flipkart.com/search?q={query.replace(' ', '%20')}"

    while True:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        for result in soup.find_all('a', class_='_4rR01T'):  # Targeting product link containers
            try:
                product_link = result.get('href')
                product_page = requests.get(product_link)
                product_soup = BeautifulSoup(product_page.content, 'html.parser')
                title_element = product_soup.find('span', {'class': 'yh-eKC'})  # Assuming title class
                price_element = product_soup.find('div', {'class': '_30jeq3'})  # Assuming price class
                image_element = product_soup.find('img', {'class': '_396cs4'})  # Assuming image class
                if title_element and price_element and image_element:
                    title = title_element.text.strip()
                    price = price_element.text.strip()
                    image_url = image_element['src']
                    products.append({"name": title, "price": price, "link": product_link, "image": image_url})
                    
                    # Store product in the database
                    cur = mysql.connection.cursor()
                    cur.execute("INSERT INTO flipkart_products (name, price, link, image) VALUES (%s, %s, %s, %s)",
                                (title, price, product_link, image_url))
                    mysql.connection.commit()
                    cur.close()
            except Exception as e:
                print("Error:", e)  # Handle potential errors during individual product page requests
        next_page = soup.find('a', {'class': '_1LKTO3'})
        if not next_page:
            break
        url = next_page['href']

    return products


def scrape_snapdeal_products(query):
    products = []
    url = f"https://www.snapdeal.com/search?keyword={query.replace(' ', '%20')}&santizedKeyword={query}&catId=0&categoryId=0&suggested=true&vertical=p&noOfResults=20&searchState=&clickSrc=suggested&lastKeyword=&prodCatId=&changeBackToAll=true&foundInAll=false&categoryIdSearched=&cityPageUrl=&categoryUrl=&url=&utmContent=&dealDetail=&sort=rlvncy"

    while True:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        for product in soup.find_all('a', rel="noopener"):  # Scraping all product links
            try:
                title_element = product.find("div", class_="product-title")
                price_element = product.find("div", class_="product-price")
                image_element = product.find("img", class_="product-image")  # Assuming image class
                if title_element and price_element and image_element:
                    title = title_element.text.strip()
                    price = price_element.text.strip()
                    image_url = image_element['src']
                    product_link = product.get('href')
                    products.append({"name": title, "price": price, "link": product_link, "image": image_url})
                    
                    # Store product in the database
                    cur = mysql.connection.cursor()
                    cur.execute("INSERT INTO snapdeal_products (name, price, link, image) VALUES (%s, %s, %s, %s)",
                                (title, price, product_link, image_url))
                    mysql.connection.commit()
                    cur.close()
            except Exception as e:
                print("Error:", e)  # Handle potential errors during individual product page requests
        next_page = soup.find('a', {'class': 'nextLink'})
        if not next_page:
            break
        url = next_page['href']

    return products





@app.route("/", methods=["GET", "POST"])
def index():
    query = request.form.get("query", "")  # Default to empty string

    

    # Handle empty query
    if not query:
        return render_template("index.html", message="No search query entered")

    # ... (rest of the code using query)

    # Move scraping logic outside conditional block
    query = request.form.get("query")  # Assuming you want to access query from form data

    # Scrape Snapdeal (if query exists)
    snapdeal_products = []
    if query:
        snapdeal_products = scrape_snapdeal_products(query)

    # Scrape Amazon (already defined)
    amazon_products = scrape_amazon_products(query)

    # Scrape Flipkart (already defined)
    flipkart_products = scrape_flipkart_products(query)

    # Combine all products (if query exists)
    all_products = []
    if query:
        all_products = snapdeal_products + amazon_products + flipkart_products

    # Handle GET or POST requests with query
    if request.method == "POST":
        if query:
            return render_template('index.html', products=all_products)
        else:
            return render_template("index.html")
    else:
        if query:
            return render_template('index.html', products=all_products)
        else:
            return render_template("index.html", message="No search query entered")

if __name__ == "__main__":
    app.run(debug=True)

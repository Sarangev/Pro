from flask import Flask, render_template, request
from bs4 import BeautifulSoup
import requests
import mysql.connector

app = Flask(__name__)

# MySQL Configuration
db_connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root@123",
    database="price_comparison"
)
cursor = db_connection.cursor()

def scrape_flipkart_and_store_to_database(query):
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


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        query = request.form["query"]
        if query:
            # Scrape Flipkart and store data in database
            scrape_flipkart_and_store_to_database(query)

            # Fetch data from database
            cursor.execute("SELECT * FROM flipkart_products")
            products = cursor.fetchall()
            return render_template('index1.html', products=products)
        else:
            return render_template("index1.html")
    else:
        return render_template("index1.html", message="No search query entered")

if __name__ == "__main__":
    app.run(debug=True)









    








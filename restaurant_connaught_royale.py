import time
import json
import csv
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

class ZomatoMenuScraper:
    def __init__(self, url="https://www.zomato.com/ncr/connaught-royale-1-connaught-place-new-delhi/order"):
        self.url = url
        self.menu_data = {}
        self.restaurant_info = {
            'name': 'Connaught Royale 1',
            'location': 'Connaught Place, New Delhi',
            'hours': '12:00 PM to 11:00 PM (Mon-Sun)',
            'contact': '+91 11 33106243'
        }
        self.setup_driver()
        
    def setup_driver(self):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
    def scrape(self):
        try:
            print(f"Opening URL: {self.url}")
            self.driver.get(self.url)
            wait = WebDriverWait(self.driver, 20)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "main")))
            time.sleep(3)
            self.handle_cookie_consent()
            self.extract_menu_categories()
            self.save_data()
            return self.menu_data
        except Exception as e:
            print(f"Error during scraping: {str(e)}")
            return None
        finally:
            self.driver.quit()
    
    def handle_cookie_consent(self):
        try:
            cookie_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept')]"))
            )
            cookie_button.click()
            time.sleep(1)
        except TimeoutException:
            pass
    
    def extract_menu_categories(self):
        try:
            sections = self.driver.find_elements(By.XPATH, "//section[.//h4]")
            print(f"Found {len(sections)} menu sections")
            for section in sections:
                try:
                    category_headers = section.find_elements(By.TAG_NAME, "h4")
                    if category_headers:
                        category_name = category_headers[0].text.strip()
                        if "₹" in section.text and len(section.text) < 100:
                            continue
                        print(f"Processing category: {category_name}")
                        self.menu_data[category_name] = []
                        self.extract_items_for_category(section, category_name)
                except Exception as e:
                    print(f"Error processing section: {e}")
            if not self.menu_data:
                print("Using alternative extraction method...")
                self.extract_by_structure()
        except Exception as e:
            print(f"Error extracting menu categories: {e}")
    
    def extract_items_for_category(self, section, category_name):
        try:
            item_containers = section.find_elements(By.XPATH, ".//div[.//h4]")
            for container in item_containers:
                item = self.extract_item_details(container)
                if item:
                    self.menu_data[category_name].append(item)
        except Exception as e:
            print(f"Error extracting items for category {category_name}: {e}")
    
    def extract_by_structure(self):
        try:
            price_elements = self.driver.find_elements(By.XPATH, "//span[contains(text(), '₹')]")
            category_name = "Menu Items"
            self.menu_data[category_name] = []
            for price_elem in price_elements:
                try:
                    container = price_elem
                    for _ in range(5):
                        container = container.find_element(By.XPATH, "..")
                        name_elems = container.find_elements(By.TAG_NAME, "h4")
                        if name_elems:
                            item = self.extract_item_details(container)
                            if item:
                                self.menu_data[category_name].append(item)
                            break
                except:
                    continue
        except Exception as e:
            print(f"Error in alternative extraction: {e}")
    
    def extract_item_details(self, container):
        try:
            item = {
                "name": "",
                "description": "",
                "price": "",
                "veg_status": "Unknown"
            }
            try:
                name_elem = container.find_element(By.TAG_NAME, "h4")
                item["name"] = name_elem.text.strip()
            except NoSuchElementException:
                return None
            try:
                price_elems = container.find_elements(By.XPATH, ".//span[contains(text(), '₹')]")
                for elem in price_elems:
                    if '₹' in elem.text:
                        item["price"] = elem.text.strip()
                        break
            except:
                pass
            if not item["price"]:
                text = container.text
                price_match = re.search(r'₹\s*(\d+)', text)
                if price_match:
                    item["price"] = f"₹{price_match.group(1)}"
            try:
                desc_elems = container.find_elements(By.TAG_NAME, "p")
                for elem in desc_elems:
                    text = elem.text.strip()
                    if text and text != item["name"] and '₹' not in text:
                        item["description"] = text
                        break
            except:
                pass
            if not item["description"]:
                full_text = container.text
                if item["name"]:
                    full_text = full_text.replace(item["name"], "", 1)
                if item["price"]:
                    full_text = full_text.replace(item["price"], "", 1)
                description = full_text.strip()
                if description:
                    item["description"] = description
            try:
                veg_indicators = container.find_elements(By.XPATH, ".//*[@type='veg']")
                if veg_indicators:
                    item["veg_status"] = "Veg"
                else:
                    non_veg_indicators = container.find_elements(By.XPATH, ".//*[@type='non-veg']")
                    if non_veg_indicators:
                        item["veg_status"] = "Non-Veg"
                    elif "Veg" in container.text and "Non-Veg" not in container.text:
                        item["veg_status"] = "Veg"
                    elif "Non-Veg" in container.text:
                        item["veg_status"] = "Non-Veg"
            except:
                pass
            if item["name"]:
                return item
            return None
        except Exception as e:
            print(f"Error extracting item details: {e}")
            return None
    
    def save_data(self):
        """Save scraped data to JSON and CSV files with restaurant metadata"""
        # Remove empty categories
        self.menu_data = {k: v for k, v in self.menu_data.items() if v}
        
        # Dictionary to track unique items by name
        unique_items = {}

       
        with open("connaught_royale_menu.json", "w", encoding="utf-8") as f:
            json.dump(self.menu_data, f, indent=4, ensure_ascii=False)
        
        
        with open("connaught_royale_menu.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Restaurant Name", "Location", "Operating Hours", "Contact",
                "Category", "Item Name", "Description", "Price", "Veg Status"
            ])
            
            for category, items in self.menu_data.items():
                for item in items:
                    item_name = item.get("name", "").strip()
                    description = item.get("description", "").strip()
                    price = item.get("price", "").strip()
                    veg_status = item.get("veg_status", "").strip()

                    # Create a unique key for each item based on its name and price
                    unique_key = (item_name, price)

                    # If the item already exists, prioritize the one with more complete information
                    if unique_key in unique_items:
                        existing_item = unique_items[unique_key]
                        if len(description) > len(existing_item["description"]) or (
                            veg_status != "Unknown" and existing_item["veg_status"] == "Unknown"
                        ):
                            unique_items[unique_key] = item
                    else:
                        unique_items[unique_key] = item

         
            for (item_name, price), item in unique_items.items():
                writer.writerow([
                    self.restaurant_info['name'],
                    self.restaurant_info['location'],
                    self.restaurant_info['hours'],
                    self.restaurant_info['contact'],
                    category,
                    item_name,
                    item.get("description", "").strip(),
                    price,
                    item.get("veg_status", "").strip()
                ])
        
        print("Data saved to connaught_royale_menu.json and connaught_royale_menu.csv")

if __name__ == "__main__":
    scraper = ZomatoMenuScraper()
    menu_data = scraper.scrape()
    if menu_data:
        total_items = sum(len(items) for items in menu_data.values())
        print(f"\nScraping completed successfully!")
        print(f"Total categories: {len(menu_data)}")
        print(f"Total menu items: {total_items}")
    else:
        print("Scraping failed.")

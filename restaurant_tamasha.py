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
    def __init__(self, url="https://www.zomato.com/ncr/tamasha-connaught-place-new-delhi/order"):
        self.url = url
        self.menu_data = {}
        self.restaurant_info = {
            'name': 'Tamasha',
            'location': '28A, Kasturba Gandhi Marg, Connaught Place, New Delhi',
            'hours': '11:30 AM to 12:30 AM (Mon-Sun)',
            'contact': '+91 11 33106409'
        }
        self.setup_driver()

    def setup_driver(self):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
    def scrape(self):
        try:
            print(f"Opening URL: {self.url}")
            self.driver.get(self.url)
            wait = WebDriverWait(self.driver, 20)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "main")))
            time.sleep(5)
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
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'accept')]"))
            )
            cookie_button.click()
            time.sleep(1)
        except TimeoutException:
            pass
    
    def extract_menu_categories(self):
        try:
            sections = self.driver.find_elements(By.TAG_NAME, "section")
            menu_sections = []
            for section in sections:
                class_attr = section.get_attribute("class")
                if class_attr and ("sc-bZVNgQ" in class_attr or "sc-" in class_attr):
                    menu_sections.append(section)
            if not menu_sections:
                headers = self.driver.find_elements(By.XPATH, "//h4[contains(@class, 'sc-')]")
                for header in headers:
                    parent = header
                    for _ in range(5):
                        parent = parent.find_element(By.XPATH, "..")
                        if parent.tag_name == "section":
                            if parent not in menu_sections:
                                menu_sections.append(parent)
                            break
            for section in menu_sections:
                self.process_menu_section(section)
        except Exception as e:
            print(f"Error extracting menu categories: {str(e)}")
    
    def process_menu_section(self, section):
        try:
            category_name = "Uncategorized"
            for tag in ["h1", "h2", "h3", "h4"]:
                headers = section.find_elements(By.TAG_NAME, tag)
                if headers:
                    category_name = headers[0].text.strip()
                    break
            if category_name == "Uncategorized":
                elements = section.find_elements(By.XPATH, ".//*[contains(@class, 'sc-') and string-length(text()) > 0]")
                for element in elements:
                    text = element.text.strip()
                    if text and ("soups" in text.lower() or "salads" in text.lower() or len(text) < 30):
                        category_name = text
                        break
            print(f"Processing category: {category_name}")
            if category_name not in self.menu_data:
                self.menu_data[category_name] = []
            self.extract_menu_items(section, category_name)
        except Exception as e:
            print(f"Error processing menu section: {str(e)}")
    
    def extract_menu_items(self, section, category_name):
        try:
            items = section.find_elements(By.XPATH, ".//div[contains(@class, 'sc-')]")
            processed_items = set()
            for item in items:
                try:
                    text_content = item.text.strip()
                    if len(text_content) < 3 or text_content in processed_items:
                        continue
                    price_match = re.search(r'₹\s*(\d+)', text_content)
                    if price_match or "item" in item.get_attribute("class").lower():
                        item_data = self.extract_item_details(item)
                        if item_data and item_data["name"]:
                            unique_key = f"{item_data['name']}-{item_data['price']}"
                            if unique_key not in processed_items:
                                self.menu_data[category_name].append(item_data)
                                processed_items.add(unique_key)
                except Exception as e:
                    continue
        except Exception as e:
            print(f"Error extracting menu items for {category_name}: {str(e)}")
    
    def extract_item_details(self, item_div):
        try:
            item = {
                "name": "",
                "description": "",
                "price": "",
                "veg_status": "Unknown",
                "image_url": ""
            }
            text_content = item_div.text.strip()
            try:
                name_elem = item_div.find_element(By.XPATH, ".//h4[contains(@class, 'sc-')]")
                item["name"] = name_elem.text.strip()
            except:
                elements = item_div.find_elements(By.XPATH, ".//*[contains(@class, 'sc-')]")
                for elem in elements:
                    text = elem.text.strip()
                    if text and len(text) < 50:
                        item["name"] = text
                        break
            if not item["name"] and text_content:
                lines = text_content.split('\n')
                if lines:
                    item["name"] = lines[0].strip()
            price_match = re.search(r'₹\s*(\d+)', text_content)
            if price_match:
                item["price"] = f"₹{price_match.group(1)}"
            try:
                desc_elem = item_div.find_element(By.XPATH, ".//span[contains(@class, 'sc-')]")
                item["description"] = desc_elem.text.strip()
            except:
                if text_content and item["name"]:
                    desc_text = text_content.replace(item["name"], "", 1).strip()
                    if item["price"]:
                        desc_text = desc_text.replace(item["price"], "", 1).strip()
                    item["description"] = desc_text
            if "Veg" in text_content:
                item["veg_status"] = "Veg"
            elif "Non-Veg" in text_content or "Non Veg" in text_content:
                item["veg_status"] = "Non-Veg"
            try:
                img_elem = item_div.find_element(By.TAG_NAME, "img")
                item["image_url"] = img_elem.get_attribute("src")
            except:
                pass
            return item
        except Exception as e:
            print(f"Error extracting item details: {str(e)}")
            return None
    
    def save_data(self):
        with open("tamasha_menu.json", "w", encoding="utf-8") as f:
            json.dump(self.menu_data, f, indent=4, ensure_ascii=False)
        with open("tamasha_menu.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Restaurant Name", "Location", "Operating Hours", "Contact",
                "Category", "Item Name", "Description", "Price", "Veg Status"
            ])
            for category, items in self.menu_data.items():
                for item in items:
                    if re.match(r'^₹\d+$', item.get("name", "").strip()):
                        continue
                    writer.writerow([
                        self.restaurant_info['name'],
                        self.restaurant_info['location'],
                        self.restaurant_info['hours'],
                        self.restaurant_info['contact'],
                        category,
                        item.get("name", ""),
                        item.get("description", ""),
                        item.get("price", ""),
                        item.get("veg_status", "")
                    ])
        print("Data saved to tamasha_menu.json and tamasha_menu.csv")

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

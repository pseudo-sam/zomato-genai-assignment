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

class DarziBarZomatoScraper:
    def __init__(self, url="https://www.zomato.com/TheDarziBar/order"):
        self.url = url
        self.menu_data = {}
        self.restaurant_info = {
            'name': 'The Darzi Bar & Kitchen',
            'location': 'Connaught Place, New Delhi',
            'hours': '11:00 AM to 1:00 AM (Daily)',
            'contact': '+91 11 3310 6409'
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
            category_elements = self.driver.find_elements(
                By.XPATH, "//p[@color='#363636' and contains(@class, 'sc-1hez2tp-0') and contains(@class, 'gdgQSV')]")
            if not category_elements:
                category_elements = self.driver.find_elements(
                    By.XPATH, "//p[contains(@class, 'sc-1hez2tp-0') and contains(@class, 'sc-1e1gAS')]")
            print(f"Found {len(category_elements)} menu categories")
            for category_elem in category_elements:
                category_text = category_elem.text.strip()
                match = re.search(r'(.*?)\s*\((\d+)\)$', category_text)
                if match:
                    category_name = match.group(1).strip()
                    item_count = match.group(2)
                    print(f"Processing category: {category_name} with {item_count} items")
                    self.menu_data[category_name] = []
                    try:
                        category_elem.click()
                        time.sleep(1)
                        self.extract_items_for_category(category_name)
                    except Exception as e:
                        print(f"Error clicking on category {category_name}: {e}")
            if not self.menu_data:
                self.extract_all_visible_items()
        except Exception as e:
            print(f"Error extracting menu categories: {e}")
    
    def extract_items_for_category(self, category_name):
        try:
            sections = self.driver.find_elements(By.TAG_NAME, "section")
            for section in sections:
                items = self.extract_menu_items_from_section(section)
                if items:
                    self.menu_data[category_name].extend(items)
                    break
        except Exception as e:
            print(f"Error extracting items for category {category_name}: {e}")
    
    def extract_menu_items_from_section(self, section):
        items = []
        try:
            item_containers = section.find_elements(By.XPATH, ".//div[.//h4]")
            for container in item_containers:
                item = self.extract_item_details(container)
                if item:
                    items.append(item)
        except Exception as e:
            print(f"Error extracting items from section: {e}")
        return items
    
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
                divs = container.find_elements(By.XPATH, ".//div[contains(@class, 'sc-')]")
                for div in divs:
                    text = div.text.strip()
                    if text and len(text) < 50:
                        item["name"] = text
                        break
            try:
                price_elem = container.find_element(By.XPATH, ".//span[contains(text(), '₹')]")
                item["price"] = price_elem.text.strip()
            except NoSuchElementException:
                spans = container.find_elements(By.XPATH, ".//span[contains(@class, 'sc-17hyc2s-1')]")
                for span in spans:
                    if '₹' in span.text:
                        item["price"] = span.text.strip()
                        break
            try:
                desc_elem = container.find_element(By.TAG_NAME, "p")
                item["description"] = desc_elem.text.strip()
            except NoSuchElementException:
                divs = container.find_elements(By.XPATH, ".//div[contains(@class, 'sc-') and string-length(text()) > 20]")
                for div in divs:
                    text = div.text.strip()
                    if text and text != item["name"] and '₹' not in text:
                        item["description"] = text
                        break
            try:
                veg_icon = container.find_element(By.XPATH, ".//use[contains(@href, '#non-veg-icon')]")
                if veg_icon:
                    item["veg_status"] = "Non-Veg"
            except NoSuchElementException:
                try:
                    veg_icon = container.find_element(By.XPATH, ".//use[contains(@href, '#veg-icon')]")
                    if veg_icon:
                        item["veg_status"] = "Veg"
                except NoSuchElementException:
                    pass
            if item["name"]:
                return item
            return None
        except Exception as e:
            print(f"Error extracting item details: {e}")
            return None
    
    def extract_all_visible_items(self):
        try:
            item_headers = self.driver.find_elements(By.TAG_NAME, "h4")
            self.menu_data["All Items"] = []
            for header in item_headers:
                try:
                    container = header
                    for _ in range(5):
                        container = container.find_element(By.XPATH, "..")
                        if container.tag_name == "div" and "sc-" in container.get_attribute("class"):
                            item = self.extract_item_details(container)
                            if item:
                                self.menu_data["All Items"].append(item)
                            break
                except Exception:
                    continue
        except Exception as e:
            print(f"Error during fallback extraction: {e}")
    
    def save_data(self):
        with open("darzi_bar_menu.json", "w", encoding="utf-8") as f:
            json.dump(self.menu_data, f, indent=4, ensure_ascii=False)
        with open("darzi_bar_menu.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Restaurant Name", "Location", "Operating Hours", "Contact",
                "Category", "Item Name", "Description", "Price", "Veg Status"
            ])
            for category, items in self.menu_data.items():
                for item in items:
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
        print("Data saved to darzi_bar_menu.json and darzi_bar_menu.csv")

if __name__ == "__main__":
    scraper = DarziBarZomatoScraper()
    menu_data = scraper.scrape()
    if menu_data:
        total_items = sum(len(items) for items in menu_data.values())
        print(f"\nScraping completed successfully!")
        print(f"Total categories: {len(menu_data)}")
        print(f"Total menu items: {total_items}")
    else:
        print("Scraping failed.")

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
    def __init__(self, url="https://www.zomato.com/ncr/local-connaught-place-new-delhi/order"):
        self.url = url
        self.menu_data = {}
        self.restaurant_info = {
            'name': 'Local',
            'location': 'Connaught Place, New Delhi',
            'hours': '12:00 PM to 1:00 AM (Mon-Sun)',
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
            category_elements = self.driver.find_elements(By.XPATH, "//p[@color='#363636' and contains(@class, 'sc-1herztp-0')]")
            if not category_elements:
                category_elements = self.driver.find_elements(By.XPATH, "//p[contains(@class, 'sc-1herztp-0') and contains(@class, 'sc-1elgAS')]")
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
                print("No categories found with specific selectors. Trying alternative approach...")
                self.extract_all_menu_items()
        except Exception as e:
            print(f"Error extracting menu categories: {e}")
    
    def extract_items_for_category(self, category_name):
        try:
            item_containers = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'sc-') and .//h4]")
            for container in item_containers:
                item = self.extract_item_details(container)
                if item:
                    self.menu_data[category_name].append(item)
        except Exception as e:
            print(f"Error extracting items for category {category_name}: {e}")
    
    def extract_all_menu_items(self):
        try:
            dish_elements = self.driver.find_elements(By.TAG_NAME, "h4")
            self.menu_data["All Items"] = []
            for dish_elem in dish_elements:
                container = dish_elem
                for _ in range(5):
                    try:
                        container = container.find_element(By.XPATH, "..")
                        price_elements = container.find_elements(By.XPATH, ".//span[contains(text(), '₹')]")
                        if price_elements:
                            item = self.extract_item_details(container)
                            if item:
                                self.menu_data["All Items"].append(item)
                            break
                    except:
                        break
        except Exception as e:
            print(f"Error in alternative extraction approach: {e}")
    
    def extract_item_details(self, container):
        try:
            item = {
                "name": "",
                "description": "",
                "price": "",
                "veg_status": "Unknown"
            }
            try:
                name_element = container.find_element(By.TAG_NAME, "h4")
                item["name"] = name_element.text.strip()
            except NoSuchElementException:
                return None
            try:
                price_elements = container.find_elements(By.XPATH, ".//span[contains(text(), '₹')]")
                if price_elements:
                    item["price"] = price_elements[0].text.strip()
                else:
                    price_elements = container.find_elements(By.XPATH, ".//span[contains(@class, 'sc-17hyc2s-1')]")
                    if price_elements:
                        item["price"] = price_elements[0].text.strip()
            except:
                pass
            try:
                desc_elements = container.find_elements(By.TAG_NAME, "p")
                if desc_elements:
                    item["description"] = desc_elements[0].text.strip()
            except:
                pass
            try:
                if "Veg" in container.text and "Non-Veg" not in container.text:
                    item["veg_status"] = "Veg"
                elif "Non-Veg" in container.text:
                    item["veg_status"] = "Non-Veg"
                veg_icons = container.find_elements(By.XPATH, ".//*[@type='veg']")
                if veg_icons:
                    item["veg_status"] = "Veg"
                else:
                    non_veg_icons = container.find_elements(By.XPATH, ".//*[@type='non-veg']")
                    if non_veg_icons:
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
        with open("local_cp_menu.json", "w", encoding="utf-8") as f:
            json.dump(self.menu_data, f, indent=4, ensure_ascii=False)
        with open("local_cp_menu.csv", "w", newline="", encoding="utf-8") as f:
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
        print("Data saved to local_cp_menu.json and local_cp_menu.csv")

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

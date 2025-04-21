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

class PunjabGrillScraper:
    def __init__(self, url="https://www.zomato.com/ncr/punjab-grill-janpath-new-delhi/order"):
        self.url = url
        self.menu_data = {}
        self.restaurant_info = {
            'name': 'Punjab Grill',
            'location': 'Janpath, New Delhi',
            'hours': '12:00 PM to 11:30 PM (Mon-Sun)',
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
            self.extract_menu_sections()
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
    
    def extract_menu_sections(self):
        try:
            section_headers = self.driver.find_elements(By.XPATH, "//h4[contains(@class, 'sc-')]")
            processed_headers = set()
            for header in section_headers:
                category_name = header.text.strip()
                if not category_name or category_name in processed_headers:
                    continue
                processed_headers.add(category_name)
                print(f"Found category: {category_name}")
                self.menu_data[category_name] = []
                parent_section = self.find_parent_section(header)
                if parent_section:
                    self.extract_items_from_section(parent_section, category_name)
            if not self.menu_data:
                print("Using alternative extraction method...")
                self.extract_by_menu_structure()
        except Exception as e:
            print(f"Error extracting menu sections: {e}")
    
    def find_parent_section(self, element):
        try:
            current = element
            for _ in range(5):
                current = current.find_element(By.XPATH, "..")
                if current.tag_name == "section":
                    return current
            return None
        except:
            return None
    
    def extract_items_from_section(self, section, category_name):
        try:
            item_containers = section.find_elements(By.XPATH, ".//div[.//h4 or .//span[contains(text(), '₹')]]")
            for container in item_containers:
                item = self.extract_item_details(container)
                if item:
                    self.menu_data[category_name].append(item)
        except Exception as e:
            print(f"Error extracting items from section {category_name}: {e}")
    
    def extract_by_menu_structure(self):
        try:
            dish_names = self.driver.find_elements(By.TAG_NAME, "h4")
            current_category = "Menu Items"
            self.menu_data[current_category] = []
            for dish_elem in dish_names:
                if self.is_likely_category_header(dish_elem):
                    current_category = dish_elem.text.strip()
                    if current_category not in self.menu_data:
                        self.menu_data[current_category] = []
                    continue
                item_container = self.find_item_container(dish_elem)
                if item_container:
                    item = self.extract_item_details(item_container)
                    if item:
                        self.menu_data[current_category].append(item)
        except Exception as e:
            print(f"Error in alternative extraction: {e}")
    
    def is_likely_category_header(self, elem):
        try:
            text = elem.text.strip()
            if re.search(r'\(\d+\)$', text) or "Dishes" in text or "Menu" in text:
                return True
            parent = elem.find_element(By.XPATH, "..")
            parent_class = parent.get_attribute("class")
            if parent_class and "header" in parent_class.lower():
                return True
            return False
        except:
            return False
    
    def find_item_container(self, dish_elem):
        try:
            current = dish_elem
            for _ in range(3):
                parent = current.find_element(By.XPATH, "..")
                if '₹' in parent.text or len(parent.find_elements(By.TAG_NAME, "span")) > 0:
                    return parent
                current = parent
            return dish_elem.find_element(By.XPATH, "..")
        except:
            return None
    
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
            except:
                return None
            try:
                price_elems = container.find_elements(By.XPATH, ".//*[contains(text(), '₹')]")
                for price_elem in price_elems:
                    price_text = price_elem.text.strip()
                    if '₹' in price_text:
                        item["price"] = price_text
                        break
            except:
                container_text = container.text
                price_match = re.search(r'₹\s*(\d+)', container_text)
                if price_match:
                    item["price"] = f"₹{price_match.group(1)}"
            try:
                desc_elems = container.find_elements(By.XPATH, ".//p | .//span[not(contains(text(), '₹'))]")
                for desc_elem in desc_elems:
                    desc_text = desc_elem.text.strip()
                    if desc_text and desc_text != item["name"] and '₹' not in desc_text:
                        item["description"] = desc_text
                        break
                if not item["description"]:
                    full_text = container.text
                    if item["name"]:
                        full_text = full_text.replace(item["name"], "", 1)
                    if item["price"]:
                        full_text = full_text.replace(item["price"], "", 1)
                    full_text = full_text.strip()
                    if full_text and "read more" in full_text:
                        item["description"] = full_text.split("read more")[0].strip()
                    elif full_text:
                        item["description"] = full_text
            except:
                pass
            if "Veg" in container.text and "Non-Veg" not in container.text:
                item["veg_status"] = "Veg"
            elif "Non-Veg" in container.text:
                item["veg_status"] = "Non-Veg"
            if item["name"]:
                return item
            return None
        except Exception as e:
            print(f"Error extracting item details: {e}")
            return None

    def save_data(self):
        self.menu_data = {k: v for k, v in self.menu_data.items() if v}
        # Deduplicate items by (category, name, description, price, veg_status)
        seen = set()
        with open("punjab_grill_menu.json", "w", encoding="utf-8") as f:
            json.dump(self.menu_data, f, indent=4, ensure_ascii=False)
        with open("punjab_grill_menu.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Restaurant Name", "Location", "Operating Hours", "Contact",
                "Category", "Item Name", "Description", "Price", "Veg Status"
            ])
            for category, items in self.menu_data.items():
                for item in items:
                    row_tuple = (
                        self.restaurant_info['name'],
                        self.restaurant_info['location'],
                        self.restaurant_info['hours'],
                        self.restaurant_info['contact'],
                        category,
                        item.get("name", ""),
                        item.get("description", ""),
                        item.get("price", ""),
                        item.get("veg_status", "")
                    )
                    if row_tuple not in seen:
                        writer.writerow(row_tuple)
                        seen.add(row_tuple)
        print("Data saved to punjab_grill_menu.json and punjab_grill_menu.csv")

if __name__ == "__main__":
    scraper = PunjabGrillScraper()
    menu_data = scraper.scrape()
    if menu_data:
        total_items = sum(len(items) for items in menu_data.values())
        print(f"\nScraping completed successfully!")
        print(f"Total categories: {len(menu_data)}")
        print(f"Total menu items: {total_items}")
    else:
        print("Scraping failed.")

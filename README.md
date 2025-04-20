# Clone the repo
git clone https://github.com/pseudo-sam/zomato-genai-assignment.git
cd zomato-genai-assignment

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # on Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run interface/app.py

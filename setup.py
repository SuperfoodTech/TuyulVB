from setuptools import setup, find_packages

setup(
    name="sf-automation",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        'gspread>=5.0.0',
        'pandas>=1.3.0',
        'selenium>=4.0.0',
        'python-dotenv>=0.19.0',
        'webdriver-manager>=3.8.0',
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="A tool to extract Grab Food data and update Google Sheets",
    python_requires='>=3.8',
)

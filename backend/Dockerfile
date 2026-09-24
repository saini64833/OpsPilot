# 1. Specify the base image
FROM python:3.10-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy the requirements file
COPY requirements.txt .

# 4. Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your backend files
COPY . .

# 6. Specify the command to run your app 
# (Adjust this if you use FastAPI/uvicorn instead of standard Python)
CMD ["python", "main.py"]
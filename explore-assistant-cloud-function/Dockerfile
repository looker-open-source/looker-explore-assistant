# Use the official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy only the required files
COPY requirements.txt ./
COPY looker_mcp_server.py ./
COPY mcp_server.py ./
COPY olympic_query_manager.py ./
COPY olympic_mcp_integration.py ./
COPY olympic_migration_manager.py ./
COPY graceful_table_manager.py ./
COPY vector_table_manager.py ./
COPY field_lookup_service.py ./
COPY enhanced_vector_integration.py ./
COPY vector_search_mcp_integration.py ./
COPY vector_table_manager.py ./
COPY llm_utils.py ./
COPY looker_reference.py ./

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Download the spaCy English model
RUN python -m spacy download en_core_web_sm

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Cloud Run will automatically set the PORT environment variable
# Set Flask environment for production
ENV FLASK_ENV=production

# Run the application
CMD ["python", "mcp_server.py"]

FROM public.ecr.aws/lambda/python:3.9-x86_64

# Install system dependencies
RUN yum update -y && yum install -y gcc

# Copy requirements and install Python dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . ${LAMBDA_TASK_ROOT}

# Command can be overwritten by providing a different command in the template directly
CMD ["main.handler"]
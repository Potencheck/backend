FROM python:3.12-slim

# 시스템 패키지 업데이트 및 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    libglib2.0-0 \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    fonts-liberation \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 아키텍처 확인
RUN dpkg --print-architecture > /tmp/arch && cat /tmp/arch

# 브라우저리스 솔루션을 대신 사용
RUN pip install --no-cache-dir playwright
RUN playwright install chromium
RUN playwright install-deps chromium

WORKDIR /app
COPY .env .env
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
COPY app app

# 디버깅을 위한 환경 변수 설정
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
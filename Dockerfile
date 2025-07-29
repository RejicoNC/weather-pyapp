FROM python:alpine

# Installer les dépendances nécessaires
RUN pip3 install flask redis requests

WORKDIR /app

# Copier le script et les templates
ADD app.py app.py
ADD templates/ templates/

CMD ["python3", "app.py"]


# Verwende ein offizielles Node.js-Image als Basis
FROM node:18-alpine

# Setze das Arbeitsverzeichnis im Container
WORKDIR /app

# Kopiere die package.json und package-lock.json in das Arbeitsverzeichnis
COPY package*.json ./

# Installiere die npm-Abhängigkeiten
RUN npm install --production

# Kopiere den restlichen Quellcode in das Arbeitsverzeichnis
COPY . .

# Definiere die Umgebungsvariable für den Port
ENV PORT=3000

# Exponiere den Port
EXPOSE 3000

# Definiere den Befehl zum Starten der Anwendung
CMD ["node", "app.js"]

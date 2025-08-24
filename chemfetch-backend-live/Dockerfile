FROM node:20-slim

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --omit=dev

# Copy source code
COPY server ./server
COPY scripts ./scripts
COPY tsconfig.json ./

# Install TypeScript and build
RUN npm install -g typescript tsx
RUN npm run build

EXPOSE 10000

CMD ["npm", "start"]

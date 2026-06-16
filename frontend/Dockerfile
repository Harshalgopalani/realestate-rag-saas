# 1. Use an official Node 20 runtime (Updated for modern Next.js compatibility)
FROM node:20-alpine

# 2. Set the working directory
WORKDIR /app

# 3. Copy the package files and install dependencies
COPY package*.json ./
RUN npm install

# 4. Copy the rest of the frontend code
COPY . .

# 5. Build the optimized production version of the Next.js app
RUN npm run build

# 6. Expose the web port
EXPOSE 3000

# 7. Start the Next.js production server
CMD ["npm", "run", "start"]
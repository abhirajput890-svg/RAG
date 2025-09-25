FROM node:18 AS build

WORKDIR /app

COPY package*.json ./

COPY . .

RUN npm run build


FROM nginx:alpine

COPY --from=build /app/build /usr/share/nginx/html

CMD ["nginx","-g","daemon-off;"] #run file in foreground


FROM node:20-alpine

WORKDIR /usr/src/app

COPY package.json yarn.lock ./

RUN yarn install --frozen-lockfile

COPY . .

ENV HOST=0.0.0.0
EXPOSE 5173

CMD ["yarn", "dev"]

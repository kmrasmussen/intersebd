# intercebd
this repo contains the code for intercebd.com

the purpose of intercebd is to be a webapp where users can log and annotate their LLM API calls, build datasets for finetuning and hopefully later also do actual finetuning

# How to run
There is an example .env file `.example.env` that should be renamed to `.env` and be filled with relevant fields.

The database is using psql neontech, you can make a free db there and put connection string 

The backend is dockerized, do
```
docker compose up
```

To run the frontend do
```
cd newmockedfrontend
npm run dev
```

The backend is in Python with FastAPI and SQLAlchemy and the swagger is localhost:9003/docs 

The frontend is on localhost:5173

If using neontech the database admin is one https://console.neon.tech/app/

# Major todos
- There is a lot with login - it creates a guest user when a guest arrives which is okay but it should be easy to logout and just not be logged in at all and have the possibility of logging in with Google.
- Make it possible to push a sft dataset to huggingface with the right conversation format, proof of concept should be able to substitute in the new dataset name instead of smoltalk everyday conversations dataset and start running finetune of qwen without problems
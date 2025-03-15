from sqlmodel import SQLModel, create_engine
from models import User, Chat, Message, Feedback

# Create a SQLite database
sqlite_url = "sqlite:///database.sqlite"
engine = create_engine(sqlite_url)

# Create tables
SQLModel.metadata.create_all(engine)

# install graphviz : sudo apt-get install graphviz
# then install these npm install -g sqleton skeleton
# then run sqleton -L dot -e -o erd.png database.sqlite
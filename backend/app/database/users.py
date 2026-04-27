from supabase import Client

from app.database.handler import DatabaseHandler
from app.database.types_autogen import (
    PublicUsers,
    PublicUsersInsert,
    PublicUsersUpdate,
)


class UsersHandler(DatabaseHandler[PublicUsers, PublicUsersInsert, PublicUsersUpdate]):
    def __init__(self, client: Client) -> None:
        super().__init__(client, table='users', row_model=PublicUsers)

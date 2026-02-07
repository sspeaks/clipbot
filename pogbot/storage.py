from dataclasses import dataclass, asdict, field
from datetime import datetime

from azure.identity import DefaultAzureCredential
from azure.data.tables import TableServiceClient, UpdateMode
from azure.storage.blob import BlobServiceClient


@dataclass
class TokenUsage:
    RowKey: str
    PartitionKey: str = field(default_factory=lambda: str(datetime.now().timestamp()))
    tokens: int = 1
    tokensSpent: int = 0
    giftedTokens: int = 50
    last_usage: float = 1669190400.0


try:
    table_account_url = "https://pogbot.table.core.windows.net/"
    blob_account_url = "https://pogbot.blob.core.windows.net/"
    default_credential = DefaultAzureCredential()

    table_service = TableServiceClient(
        endpoint=table_account_url, credential=default_credential
    )
    blob_service = BlobServiceClient(blob_account_url, credential=default_credential)

    container_name = "dalleimages"
    table_name = "tokenUsages"
    try:
        table_service.create_table(table_name)
        print("Table created!")
        blob_service.create_container(container_name)
    except Exception:
        pass
    table_client = table_service.get_table_client(table_name=table_name)

except Exception as ex:
    print("Exception:")
    print(ex)
    exit()


def upload_image_to_container(filepath, blob_name):
    blob_client = blob_service.get_blob_client(container=container_name, blob=blob_name)
    with open(file=filepath, mode="rb") as data:
        blob_client.upload_blob(data)


def get_entity_from_user(user):
    user_filter = f"RowKey eq '{user.name}'"
    entities = list(table_client.query_entities(user_filter))
    if len(entities) != 1:
        return TokenUsage(RowKey=user.name)
    [temp_entity] = entities
    return TokenUsage(**dict(temp_entity))


def remove_one_token_from_user(user):
    entity = get_entity_from_user(user)
    if entity.giftedTokens > 0:
        entity.giftedTokens -= 1
    else:
        entity.tokens -= 1
        entity.tokensSpent += 1
    update_entity(entity)


def update_entity(entity):
    table_client.upsert_entity(mode=UpdateMode.REPLACE, entity=asdict(entity))


def get_updated_tokens_for_user(user):
    entity = get_entity_from_user(user)
    old_usage = datetime.fromtimestamp(entity.last_usage)
    new_usage = datetime.now()
    weeks = (new_usage - old_usage).days // 7
    total_tokens = entity.tokens + entity.tokensSpent
    if total_tokens <= weeks + 1:  # Less than or equal to so I can gift people tokens
        entity.tokens = (weeks + 1) - entity.tokensSpent
    update_entity(entity)
    return entity.tokens + entity.giftedTokens

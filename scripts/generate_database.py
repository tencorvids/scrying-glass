import imagehash
import requests
import psycopg2
from PIL import Image
import os
from dotenv import find_dotenv, load_dotenv

dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

DB_NAME = os.getenv("DATABASE")
DB_USER = os.getenv("USER")
DB_PASSWORD = os.getenv("PASSWORD")
DB_HOST = os.getenv("HOST")
DB_PORT = os.getenv("PORT")

def get_bulk_data():
    # bulk types: [default_cards, oracle_cards, unique_artwork, all_cards, rulings]

    BULK_METADATA_URI = 'https://api.scryfall.com/bulk-data'
    BULK_METADATA_TYPE = 'default_cards'
    BULK_DEFAULT_METADATA_URI = BULK_METADATA_URI + '/' + BULK_METADATA_TYPE

    bulk_metadata = requests.get(BULK_DEFAULT_METADATA_URI).json()
    bulk_download_uri = bulk_metadata['download_uri']

    bulk_data = requests.get(bulk_download_uri).json()
    return bulk_data

def get_image_uri(card):
    image_uri = card['image_uris']['large']

    if image_uri == '':
        image_uri = card['image_uris']['normal']

    if image_uri == '':
        image_uri = card['image_uris']['small']

    return image_uri

def image_from_uri(uri):
    try:
        image = Image.open(requests.get(uri, stream=True).raw)
        return image
    except:
        return None

def validate_card(card):
    digital_only = card['digital']
    image_status = card['image_status'] != 'highres_scan'
    image_uri_status = 'image_uris' not in card.keys()

    if digital_only or image_status or image_uri_status:
        return False

    return True

def main():
    db_connection = psycopg2.connect(database=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
    db_cursor = db_connection.cursor()

    bulk_data = get_bulk_data()
    print('\n\n')

    for i, card in enumerate(bulk_data):
        try:
            if i % 50 == 0:
                print('Card ' + str(i) + ' of ' + str(len(bulk_data)))

            if not validate_card(card):
                continue

            image_uri = get_image_uri(card)
            if image_uri is None:
                continue

            # can be null
            tcgplayer_id = card['tcgplayer_id'] if 'tcgplayer_id' in card.keys() else -1
            tcgplayer_etched_id = card['tcgplayer_etched_id'] if 'tcgplayer_etched_id' in card.keys() else -1
            cardmarket_id = card['cardmarket_id'] if 'cardmarket_id' in card.keys() else -1
            mana_cost = card['mana_cost'] if 'mana_cost' in card.keys() else ''
            oracle_text = card['oracle_text'] if 'oracle_text' in card.keys() else 'N/A'
            power = card['power'] if 'power' in card.keys() else 'N/A'
            toughness = card['toughness'] if 'toughness' in card.keys() else 'N/A'
            artist = card['artist'] if 'artist' in card.keys() else 'N/A'
            flavor_name = card['flavor_name'] if 'flavor_name' in card.keys() else 'N/A'
            flavor_text = card['flavor_text'] if 'flavor_text' in card.keys() else 'N/A'

            # cannot be null
            scryfall_id = card['id'] if 'id' in card.keys() else None
            language = card['lang'] if 'lang' in card.keys() else None
            rulings_uri = card['rulings_uri'] if 'rulings_uri' in card.keys() else None
            scryfall_uri = card['scryfall_uri'] if 'scryfall_uri' in card.keys() else None
            cmc = card['cmc'] if 'cmc' in card.keys() else None
            name = card['name'] if 'name' in card.keys() else None
            type_line = card['type_line'] if 'type_line' in card.keys() else None
            collector_number = card['collector_number'] if 'collector_number' in card.keys() else None
            rarity = card['rarity'] if 'rarity' in card.keys() else None
            set_name = card['set_name'] if 'set_name' in card.keys() else None

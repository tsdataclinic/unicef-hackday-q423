import ts3
from io import StringIO
import pandas as pd
import geopandas as gpd
import requests_tsauth
import zipfile
import tempfile
import shutil
import io
import os

session = requests_tsauth.Session(use_proxies=True)
client = client = ts3.get_ts3_client()


def load_data(bucket, path):
    """
    Loads a csv from ts3
    """
    
    client = ts3.get_ts3_client()

    response = client.get_object(
            Bucket= bucket, Key = path
    )

    bytes = response["Body"].read()
    if path[-3:] == "csv":
        s = str(bytes, "utf-8")
        data = StringIO(s)
        df = pd.read_csv(data, low_memory=False, index_col=0)
    elif path[-7:] == "geojson":
        s = str(bytes, "utf-8")
        data = StringIO(s)
        df = gpd.read_file(data)
    elif path[-3:] == "shp":
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Assume all related files have the same prefix in their name
            prefix = os.path.splitext(path)[0]

            # Get a list of all related files
            result = client.list_objects(Bucket=bucket, Prefix=prefix)
            for item in result.get('Contents', []):
                file_path = item.get('Key')
                if file_path:
                    # Download each file to the temporary directory
                    client.download_file(bucket, file_path, os.path.join(tmp_dir, os.path.basename(file_path)))

            # Now all related files should be in tmp_dir and you can read them as usual
            df = gpd.read_file(os.path.join(tmp_dir, os.path.basename(path)))
    elif path[-4:] == "xlsx":
        data = io.BytesIO(bytes)
        df = pd.read_excel(data, engine='openpyxl')
    return df

def write_to_ts3(df, bucket, path):
    
    """
    Writes a file out to ts3
    """
    client = ts3.get_ts3_client()

    if path[-3:] == "csv":
        df_save = df.to_csv()
    elif path[-7:] == "geojson":
        df_save = df.to_json()
        
    client.put_object(
        Bucket=bucket, Key=path, Body=df_save
    )

def read_shapefile_from_url(url):

    """Downloads, extracts and reads a zipped shapefile from a url"""
    
    response = session.get(url)

    zipfile_io = io.BytesIO(response.content)
    temp_dir = tempfile.mkdtemp()

    with zipfile.ZipFile(zipfile_io) as zip_file:
        zip_file.extractall(path=temp_dir)

    shapefile_name = None

    for dirName, subdirList, fileList in os.walk(temp_dir):
        for fname in fileList:
            if fname.endswith(".shp"):
                shapefile_name = f"{dirName}/{fname}"

    if shapefile_name is not None:
        gdf = gpd.read_file(os.path.join(temp_dir, shapefile_name))
    else:
        print('No shapefile found in the zip file.')
    shutil.rmtree(temp_dir)

    return gdf
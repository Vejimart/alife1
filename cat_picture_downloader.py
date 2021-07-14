import os
from datetime import datetime
from PIL import Image, ImageOps
from time import sleep
import requests
import io


image_url = "https://thiscatdoesnotexist.com/"

mask_path = os.path.join("res", "circle_mask_50x50.png")

download_path = os.path.join("res", "cats")

max_pictures = 2000

exit_loop = False
while not exit_loop:
    picture_count = len(os.listdir(download_path))
    now = datetime.now()
    if picture_count < max_pictures:
        datetimestring = now.strftime("%Y-%m-%d-%H-%M-%S-%f")
        timestring = now.strftime("%H:%M:%S")
        print(picture_count, "cat pictures")
        print("started download at ", timestring)

        try:
            r = requests.get(image_url, timeout=1)
            im = Image.open(io.BytesIO(r.content))

            # https://stackoverflow.com/questions/890051/how-do-i-generate-circular-thumbnails-with-pil
            mask = Image.open(mask_path).convert('L')
            output = ImageOps.fit(im, mask.size, centering=(0.5, 0.5))
            output.putalpha(mask)

            filepath_output = os.path.join(download_path, datetimestring + ".png")

            output.save(filepath_output)
            print("New picture succesful: ", filepath_output)
        except Exception as e:
            print("Could not download picture")
    else:
        print("Done!")
        exit_loop = True

    # Wait some time between requests, just in case...
    sleep(1)

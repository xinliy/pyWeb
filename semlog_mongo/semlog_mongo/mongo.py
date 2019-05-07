from pymongo import MongoClient
import os
import gridfs
import shutil
from multiprocessing import Pool


class MongoDB():

    def __init__(self, database, collection, ip='127.0.0.1', port=27017):
        self.database = database
        self.collection = collection
        self.client = MongoClient(ip, port)[database][collection]
        self.ip=ip
        self.port=port

    def search(self, timestamp=None, object_id=None, view_id=None, image_type=None):
        """Input params to search for specific images.

        Args:
            timestamp(float): Filter out images taken larger than the timestamp.
            object_id(str): Id for a specific object.
            view_id(str): Id for a specific view.
            image_type(str): type for images. ("Color"|"Normal"|"Depth"|"Mask")

        Return:
            Result from the MongoDB.

        """

        pipeline = [{"$match": {"views": {"$exists": True}}}]

        if timestamp is not None:
            pipeline.append({"$match": {"timestamp": {"$lte": timestamp}}})
        pipeline.append({"$unwind": {"path": "$views"}})
        if object_id is not None:
            pipeline.append({"$match": {"views.entities.id": object_id}})

        if view_id is not None:
            pipeline.append({"$match": {"views.id": view_id}})
        pipeline.append({"$project": {"views.images": 1}})

        if image_type is not None:
            pipeline.append({"$unwind": {"path": "$views.images"}})
            pipeline.append({"$match": {"views.images.type": image_type}})
        return list(self.client.aggregate(pipeline))

    def download(self, image_list, abs_path=''):
        """Download images depending on the given image id list.

            Args:
                image_list: Result from the MongoDB.
                abs_path: absolute path for saving images.


        """
        print("Start downloading images.")
        print("Length of image_list:",len(image_list))
        dic = {'Color': [], 'Depth': [], 'Mask': [], 'Normal': []}
        img_dir={'Color': [], 'Depth': [], 'Mask': [], 'Normal': []}
        for images in image_list:
            # One type, one instance is a dict, or multi dicts in a list
            if type(images['views']['images']) == dict:
                im = images['views']['images']
                dic[im['type']].append(im['file_id'])
            else:
                for image in images['views']['images']:
                    dic[image['type']].append(image['file_id'])

        for image_type, image_id_list in dic.items():
            if len(image_id_list) == 0:
                break
            print(image_type, len(image_id_list))
            path=os.path.join(abs_path,image_type)
            # Delete old folder.
            if os.path.exists(path):
                shutil.rmtree(path)
            os.makedirs(path)

            download_db = gridfs.GridFSBucket(
                MongoClient(self.ip,self.port)[self.database], self.collection)

            for i in image_id_list:
                img_path=os.path.join(path,str(i)+".png")
                file = open(img_path, "wb+")

                if "Color" in img_path:
                    img_dir['Color'].append(img_path)
                elif "Depth" in img_path:
                    img_dir['Depth'].append(img_path)
                elif "Mask" in img_path:
                    img_dir['Mask'].append(img_path)
                elif "Normal" in img_path:
                    img_dir['Normal'].append(img_path)
                download_db.download_to_stream(file_id=i, destination=file)
        print("Finish downloading.")
        print("img_dir",img_dir)
        return img_dir

    def get_object_rgb(self,object_id,collection):
        client=MongoClient(self.ip,self.port)[self.database][collection]["meta"]
        pipline=[]
        pipline.append({"$unwind":{"path":"$env.entities"}})
        pipline.append({"$match":{"env.entities.id":object_id}})
        pipline.append({"$project":{"env.entities.mask_hex":1}})
        h=list(client.aggregate(pipline))[0]['env']['entities']['mask_hex']
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    # @staticmethod
    # def save_json(data, path):
    #
    #     for i in data:
    #         print(i)
    #
    #     data = dumps(data,json_options=RELAXED_JSON_OPTIONS)
    #     # data=data.replace('\"','')
    #
    #     print("type",type(data))
    #     with open(path, 'w') as outfile:
    #         json.dump(data, outfile)
    #     print("Saved json data to:", path)

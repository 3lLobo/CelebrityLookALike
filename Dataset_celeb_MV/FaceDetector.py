import face_recognition
import os
import numpy as np
import pandas as pd
import glob
from PIL import Image
from tqdm import tqdm
import math
from multiprocessing import Process, Manager
import time

#(!) Code that doesnt work yet
#def get_face_encodings_multiprocessorHandler(self):
#    with Manager() as manager:
#        L = manager.list()  # <-- can be shared between processes.
#        processes = [None for i in self.input_images]
#    for i, file in enumerate(tqdm(self.input_images)):
#        print(i)
#        processes[i] = Process(target=FaceDetector.get_face_encodings_multiprocessor, args=(self, L, file))  # Passing the list
#        processes[i].start()
#        time.sleep(5)
#    for process in processes:
#        process.join()
#    print(L)
#    self.known_encodings = L

class FaceDetector:
    def __init__(self,inputFolder, inputFolder_celeb):
        self.input_dataset = pd.read_csv(filepath_or_buffer=os.getcwd() + inputFolder +'DataSet.csv')
        self.input_dataset['PhotoLocation'] = str(os.getcwd()) + str(inputFolder) + self.input_dataset['SamAccountName'].astype(str) + str('.jpg')
        self.input_images = self.input_dataset['PhotoLocation'].tolist()

        self.input_dataset_celeb = pd.read_csv(filepath_or_buffer=os.getcwd() + inputFolder_celeb +'DataSet.csv')
        self.input_dataset_celeb['PhotoLocation'] = str(os.getcwd()) + str(inputFolder_celeb) + self.input_dataset_celeb['SamAccountName'].astype(str) + str('.jpg')
        self.input_images_celeb = self.input_dataset_celeb['PhotoLocation'].tolist() 
        #self.input_images = list(glob.glob(os.getcwd() + inputFolder + '*.jpg'))
        # print(self.input_dataset)
        # print(self.input_images)
        
        self.known_encodings = []
        self.names = []
        self.face_distances = []

        self.known_encodings_celeb = []
        self.names_celeb = []
        self.face_distances_celeb = []

    
    #def get_face_encodings_multiprocessor(self, multiprocessorList, file):
    #    #self.names.append(file.split('/')[-1][:-4])
    #    known_image = face_recognition.load_image_file(file)
    #    try:
    #        face_encoding = face_recognition.face_encodings(known_image)[0]
    #    except Exception as e:
    #        print('No face detected - dumping trace')
    #        print(e)
    #    multiprocessorList.append(face_encoding)

    def get_face_encodings(self):
        with tqdm(total=len(self.input_images)):
            for file in tqdm(self.input_images):
                #print(file)
                self.names.append(file.split('/')[-1][:-4])
                known_image = face_recognition.load_image_file(file)
                try:
                    face_encoding = face_recognition.face_encodings(known_image)[0]
                except Exception as e:
                    print('No face detected - dumping trace')
                    print(file)
                    print(e)
                self.known_encodings.append(face_encoding)

        with tqdm(total=len(self.input_images_celeb)):
            for file in tqdm(self.input_images_celeb):
                #print(file)
                self.names_celeb.append(file.split('/')[-1][:-4])
                known_image = face_recognition.load_image_file(file)
                try:
                    face_encoding = face_recognition.face_encodings(known_image)[0]
                except Exception as e:
                    print('No face detected - dumping trace')
                    print(file)
                    print(e)
                self.known_encodings_celeb.append(face_encoding)

    def get_lookalike(self, input_image_path, imageXY):
        # Load a test image and get encodings for it
        image_to_test = face_recognition.load_image_file(input_image_path)
        
        #First we find the middle person and take their picture -- if there is one!
        faceLocations = face_recognition.api.face_locations(img=image_to_test)

        #We found zero people in the pic -- abort!
        if(len(faceLocations)==0):    
            raise ValueError("We didn't find your face")
        
        #Calculate avgX,avgY for every face
        faceLocations = pd.DataFrame(data=faceLocations, columns=['Top','Right','Bottom','Left'])
        faceLocations['avgX'] = (faceLocations['Right']+faceLocations['Left'])/2
        faceLocations['avgY'] = (faceLocations['Top']+faceLocations['Bottom'])/2
        faceLocations['avgXY'] = list(zip(faceLocations['avgX'], faceLocations['avgY']))

        #Determine the middle point of the image
        middleXY = (imageXY[0]/2,imageXY[1]/2,)
        
        #And determine the closest person to the middle point
        def distance(p1, p2):
            return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
        middleFace = min(faceLocations['avgXY'], key=lambda x: distance(x, middleXY))

        #Find the middle face in pandas dataframe and reset the index so the first record has index[0]
        known_face_location = faceLocations.loc[faceLocations['avgXY'] == middleFace].reset_index(drop=True)
        #print(known_face_location)
        #Create a list of 1 tuple with the middle face location
        known_face_location=[(known_face_location['Top'][0],known_face_location['Right'][0],known_face_location['Bottom'][0],known_face_location['Left'][0],)]

        #Easy - now we have just one person!
        #Get the face encoding
        image_to_test_encoding = face_recognition.face_encodings(face_image=image_to_test, known_face_locations=known_face_location)[0]
        #See how far apart the test image is from the known faces
        face_distances = face_recognition.face_distance(self.known_encodings, image_to_test_encoding)
        face_distances_celeb = face_recognition.face_distance(self.known_encodings_celeb, image_to_test_encoding)
        #Sort the list and keep the sorted indexes of the original in order of value (asc sort)
        lookalike_indexes = sorted(range(len(face_distances)), key=lambda k: face_distances[k])
        lookalike_indexes_celeb = sorted(range(len(face_distances_celeb)), key=lambda k: face_distances_celeb[k])

        #Prepare return variables
        lookalike_index_self = lookalike_indexes[0]
        lookalike_image_path_self = self.input_images[lookalike_index_self]
        lookalike_index_celeb= lookalike_indexes_celeb[0]
        lookalike_image_path_celeb = self.input_images_celeb[lookalike_index_celeb]

        check_recognized = face_distances[lookalike_index_self]
        # print(check_recognized)
        # print(lookalike_image_path_self)

        if check_recognized > 0.6:
            lookalike_index_self = -1
            # lookalike_index_similar = lookalike_indexes [0]
            lookalike_image_path_self = "./assets/not_recognized.png"
            # lookalike_image_path_similar = self.input_images[lookalike_index_similar]

        print(lookalike_index_self)
        
        return face_distances, lookalike_index_self, lookalike_image_path_self, lookalike_index_celeb, lookalike_image_path_celeb

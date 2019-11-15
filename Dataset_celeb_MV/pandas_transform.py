import pandas as pd
import csv

df = pd.read_csv('labels2.csv')

labels = pd.DataFrame(columns=['Givenname', 'Surname', 'SamAccountName'])
labels['Givenname'] = df['Name']
labels['Surname'][:] = [' ']*(int(labels.index[-1])+1)
labels['SamAccountName'] = df['ObjectClass']

print(labels)

labels.to_csv('./input/DataSet.csv')

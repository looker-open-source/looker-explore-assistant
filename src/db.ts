/*

 Copyright 2023 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

 */


/**
 * This file contains the IndexedDB logic for storing and retrieving chat messages for explore assistant
 */


let request: IDBOpenDBRequest;
let db: IDBDatabase;
let version = 1;

export enum Stores {
  Chat = 'chat',
}

export const initDB = () => {
  return new Promise((resolve) => {
    // open the connection
    request = indexedDB.open('myDB',1);

    request.onupgradeneeded = (e) => {
      console.log("here")
      db = e.target?.result;
    
      // if the data object store doesn't exist, create it
      if (!db.objectStoreNames.contains(Stores.Chat)) {
        console.log('Creating chat store');
        db.createObjectStore(Stores.Chat,{autoIncrement:true})
      }
    };

    request.onsuccess = () => {
      db = request.result;
      version = db.version;

      console.log('request.onsuccess - initDB', version);
      resolve(true);
    };

    request.onerror = () => {
      resolve(false);
    };
  });
};

export const addData = (storeName:string, data: any, key?: string) => {
    return new Promise((resolve) => {
      request = indexedDB.open('myDB', version);
  
      request.onsuccess = () => {
        db = request.result;
        const tx = db.transaction(storeName, 'readwrite');
        const store = tx.objectStore(storeName);
        store.add(data);
        resolve(data);
      };
  
      request.onerror = () => {
        const error = request.error?.message
        if (error) {
          resolve(error);
        } else {
          resolve('Unknown error');
        }
      };
    });
  };

  export const getStoreData = (storeName: string) => {
    return new Promise((resolve) => {
      request = indexedDB.open('myDB');
  
      request.onsuccess = () => {
        db = request.result;
        const tx = db.transaction(storeName, 'readonly');
        const store = tx.objectStore(storeName);
        const res = store.getAll();
        res.onsuccess = () => {
          resolve(res.result);
        };
      };
    });
  };
/*

MIT License

Copyright (c) 2023 Looker Data Sciences, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

*/

/**
 * This file contains the IndexedDB logic for storing and retrieving chat messages for explore assistant
 */

let request: IDBOpenDBRequest
let db: IDBDatabase
let version = 1

export enum Stores {
  Chat = 'chat',
}

/**
 * Initializes the database connection.
 * @returns A promise that resolves to a boolean indicating whether the database connection was successfully established.
 */
export const initDB = () => {
  return new Promise((resolve) => {
    // open the connection
    request = indexedDB.open('myDB', 1)

    request.onupgradeneeded = (e) => {
      db = e.target?.result

      // if the data object store doesn't exist, create it
      if (!db.objectStoreNames.contains(Stores.Chat)) {
        db.createObjectStore(Stores.Chat, { autoIncrement: true })
      }
    }

    request.onsuccess = () => {
      db = request.result
      version = db.version
      resolve(true)
    }

    request.onerror = () => {
      resolve(false)
    }
  })
}

/**
 * Adds data to the specified store in IndexedDB.
 * @param storeName - The name of the store to add data to.
 * @param data - The data to be added to the store.
 * @returns A promise that resolves with the added data or an error message.
 */
export const addData = (storeName: string, data: any) => {
  return new Promise((resolve) => {
    request = indexedDB.open('myDB', version)

    request.onsuccess = () => {
      db = request.result
      const tx = db.transaction(storeName, 'readwrite')
      const store = tx.objectStore(storeName)
      store.add(data,data.message)
      resolve(data)
    }

    request.onerror = () => {
      const error = request.error?.message
      if (error) {
        resolve(error)
      } else {
        resolve('Unknown error')
      }
    }
  })
}

/**
 * Retrieves data from the specified object store in the indexedDB.
 * @param storeName - The name of the object store to retrieve data from.
 * @returns A promise that resolves with the retrieved data.
 */
export const getStoreData = (storeName: string) => {
  return new Promise((resolve) => {
    request = indexedDB.open('myDB')

    request.onsuccess = () => {
      db = request.result
      const tx = db.transaction(storeName, 'readonly')
      const store = tx.objectStore(storeName)
      const res = store.getAll()
      res.onsuccess = () => {
        resolve(res.result)
      }
    }
  })
}

/**
 * Retrieves data from the specified object store and key in the indexedDB.
 * @param storeName - The name of the object store to retrieve data from.
 * @param key - The key of the row to fetch data from
 * @returns A promise that resolves with the retrieved data.
 */
export const getData = (storeName: string, key: string) => {
  return new Promise((resolve) => {
    request = indexedDB.open('myDB')

    request.onsuccess = () => {
      db = request.result
      const tx = db.transaction(storeName, 'readonly')
      const store = tx.objectStore(storeName)
      const res = store.get(key)
      res.onsuccess = () => {
        resolve(res.result)
      }
    }
  })
}


/**
 * Updates data from the specified object store at a given key in the indexedDB.
 * @param storeName - The name of the object store to retrieve data from.
 * @param key - The key to update data at.
 * @param value - The value to update at the given key.
 * @returns A promise that resolves with the successful update.
 */
export const updateData = (storeName: string, key:string, value: any) => {
  return new Promise((resolve) => {
    request = indexedDB.open('myDB')

    request.onsuccess = () => {
      db = request.result
      const tx = db.transaction(storeName, 'readwrite')
      const store = tx.objectStore(storeName)
      const res = store.put(value,key)
      res.onsuccess = () => {
        resolve(res)
      }
    }
  })
}

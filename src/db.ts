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
      console.log('here')
      db = e.target?.result

      // if the data object store doesn't exist, create it
      if (!db.objectStoreNames.contains(Stores.Chat)) {
        console.log('Creating chat store')
        db.createObjectStore(Stores.Chat, { autoIncrement: true })
      }
    }

    request.onsuccess = () => {
      db = request.result
      version = db.version

      console.log('request.onsuccess - initDB', version)
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
      store.add(data)
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

/*

 MIT License

 Copyright (c) 2022 Looker Data Sciences, Inc.

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

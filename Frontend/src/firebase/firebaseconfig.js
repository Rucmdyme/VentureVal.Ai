// firebase.js
import { initializeApp } from "firebase/app";
import { getStorage } from "firebase/storage";

const firebaseConfig = {
  apiKey: "AIzaSyB5Ulk0FI3uwbSWhU848_PON3C730vpWc8",
  authDomain: "ventureval-ef705.firebaseapp.com",
  projectId: "ventureval-ef705",
  storageBucket: "ventureval-ef705.firebasestorage.app",
  messagingSenderId: "1094484866096",
  appId: "1:1094484866096:web:9f91ef1c563dd7a5bca9f5",
  measurementId: "G-WCCL05HBGM",
};

const app = initializeApp(firebaseConfig);
export const storage = getStorage(app);

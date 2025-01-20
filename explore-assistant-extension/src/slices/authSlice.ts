import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  isAuthenticated: false,
  access_token: null,
  expires_in: null
};

export const authSlice = createSlice({
  name: 'auth',
  initialState,  // Just reference the initialState constant here
  reducers: {
    setAuthenticated: (state, action) => {
      state.isAuthenticated = action.payload;
    },
    setToken: (state, action) => {
      state.access_token = action.payload;
    },
    setExpiry: (state, action) => {
      state.expires_in = action.payload;
    }
  }
});

export const { setAuthenticated, setToken, setExpiry } = authSlice.actions;


// File: src/App.js
import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Login from './components/Login';
import ApplyForm from './components/ApplyForm';
import ApplyFormProgramDop from './components/ApplyFormProgramDop';
import ApplyFormProgramPop from './components/ApplyFormProgramPop';
import ListApplicationsLeader from './components/ListApplicationsLeader';
import PrivateRoute from './components/PrivateRoute';
import Layout from './components/Layout';

function App() {
  const handleApplySubmit = selectedOption => {
    // TODO: replace with navigation or state update as needed
  };
  return (
    <BrowserRouter>
      <Routes>
        {/* Public route */}
        <Route path="/" element={<Login />} />

        {/* All other routes get the sidebar + topbar */}
        <Route element={<Layout />}>
          <Route
            path="/prijava-bivak"
            element={
              <PrivateRoute>
                <ApplyForm onSubmit={handleApplySubmit} />
              </PrivateRoute>
            }
          />
          <Route
            path="/prijava-program-dop"
            element={
              <PrivateRoute>
                <ApplyFormProgramDop onSubmit={handleApplySubmit} />
              </PrivateRoute>
            }
          />
          <Route
            path="/prijava-program-pop"
            element={
              <PrivateRoute>
                <ApplyFormProgramPop onSubmit={handleApplySubmit} />
              </PrivateRoute>
            }
          />
          <Route
            path="/prijave-clani"
            element={
              <PrivateRoute>
                <ListApplicationsLeader onSubmit={handleApplySubmit} />
              </PrivateRoute>
            }
          />
          {/* add more protected routes here */}
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
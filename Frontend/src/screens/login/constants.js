export const LOGIN_FORM_CONFIG = {
  roles: ["Investor", "Entrepreneur", "Advisor"],

  common: [
    { name: "full_name", label: "Full Name", type: "text", signupOnly: true },
    { name: "email", label: "Email", type: "email" },
    { name: "password", label: "Password", type: "password" },
  ],
  roleSpecific: {
    Entrepreneur: [
      { name: "startup_name", label: "Startup Name", type: "text" },
      {
        name: "stage",
        label: "Stage",
        type: "select",
        options: [
          "Idea",
          "MVP",
          "Revenue",
          "Scaling",
          "Seed",
          "Series A",
          "Series B",
        ],
      },
      {
        name: "sector",
        label: "Sector",
        type: "text",
        placeholder: "e.g., FinTech, HealthTech, AI/ML",
      },
    ],
    Investor: [
      {
        name: "investment_stages",
        label: "Investment Stage Preference",
        type: "multiselect",
        options: [
          "Idea",
          "MVP",
          "Revenue",
          "Scaling",
          "Seed",
          "Series A",
          "Series B",
        ],
      },
      {
        name: "sectors_of_interest",
        label: "Sectors of Interest",
        type: "text",
        placeholder: "e.g., FinTech, HealthTech, AI/ML",
      },
    ],
    Advisor: [
      { name: "organization", label: "Organization", type: "text" },
      { name: "designation", label: "Designation", type: "text" },
      {
        name: "focus_area",
        label: "Focus Area",
        type: "text",
        placeholder: "e.g., Due diligence, Management, Deal Sourcing",
      },
    ],
  },
};

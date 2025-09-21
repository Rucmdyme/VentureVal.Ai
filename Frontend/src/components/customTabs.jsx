// src/components/CustomTabs.js
import React from "react";
import { Tabs, Tab, Box } from "@mui/material";

const CustomTabs = ({ tab, setTab, tabsConfig }) => {
  return (
    <Box
      sx={{
        bgcolor: "grey.300",
        borderRadius: 5,
        px: 1,
        display: "flex",
        justifyContent: "center",
        my: 2,
      }}
    >
      <Tabs
        value={tab}
        onChange={(_, value) => setTab(value)}
        variant="fullWidth"
        slotProps={{
          indicator: { style: { display: "none" } },
        }}
        sx={{
          "& .MuiTab-root": {
            textTransform: "none",
            minHeight: 40,
            minWidth: 120,
            borderRadius: 20,

            "&.Mui-selected": {
              bgcolor: "white",
              fontWeight: "bold",
            },
          },
          "& .MuiTabs-scroller": {
            display: "flex",
            alignItems: "center",
          },
          "& .MuiTabs-list": {
            width: "100%",
          },
          width: "100%",
        }}
      >
        {tabsConfig.map((tab) => (
          <Tab
            key={tab.key}
            value={tab.key}
            icon={tab.icon}
            label={tab.label}
            iconPosition="start"
            disableRipple
            sx={{ color: "black" }}
          />
        ))}
      </Tabs>
    </Box>
  );
};

export default CustomTabs;

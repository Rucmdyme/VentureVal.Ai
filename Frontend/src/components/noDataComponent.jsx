import React from "react";

//material imports
import { Box } from "@mui/material";

//helper functions
import EmptyImage from "../assets/empty.svg";
const NoDataComponent = ({ loader, containerSx = {} }) => {
  return (
    <Box
      textAlign="center"
      hidden={loader}
      sx={{ margin: containerSx?.["margin"] || "50px auto", ...containerSx }}
    >
      <img src={EmptyImage} alt="empty_image" draggable={false} />
    </Box>
  );
};
export default NoDataComponent;

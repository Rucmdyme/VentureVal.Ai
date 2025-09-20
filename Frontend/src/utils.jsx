export const snakeCaseToTitleCase = (str = "", splitBy = "") => {
  const regex = splitBy === "space" ? /[ _]+/ : /_+/;
  return str
    ?.split(regex)
    ?.map((w) => (w[0] ? w[0]?.toUpperCase() + w.slice(1).toLowerCase() : ""))
    ?.join(" ");
};

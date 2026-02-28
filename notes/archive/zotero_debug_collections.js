// Run in Zotero: Tools > Developer > Run JavaScript
// Check "Run as async function"
// This lists ALL collections so we can see exact names

const allCollections = Zotero.Collections.getByLibrary(Zotero.Libraries.userLibraryID);
let output = `Total collections: ${allCollections.length}\n\n`;

for (const col of allCollections) {
  const parentID = col.parentID;
  const parentName = parentID ? Zotero.Collections.get(parentID).name : "(top-level)";
  output += `ID: ${col.id} | Parent: ${parentName} | Name: "${col.name}"\n`;
}

return output;

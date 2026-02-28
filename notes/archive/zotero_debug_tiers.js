// Get ALL collections including subcollections
var libraryID = Zotero.Libraries.userLibraryID;
var collections = Zotero.Collections.getByLibrary(libraryID, true);
var output = [];
for (let c of collections) {
    if (c.name.includes("Tier") || c.name.includes("To Read") || c.parentID === 32) {
        output.push(c.name + " | key=" + c.key + " | id=" + c.id + " | parentID=" + c.parentID);
    }
}
return output.join("\n");

// Add papers to tiers via item.addToCollection()
var libraryID = Zotero.Libraries.userLibraryID;
var added = 0;
var errors = [];

var tiers = {
    33: ["MAK7JGZQ","FWKEC6IS"],
    34: ["VWSFDYJY","FYPM6N4Q","3PV7NVDG","PFHEXKMA","EWWEJ7KA"],
    35: ["IHP5KR5A","96EI7Y86","EMJ8ES9G","8CPP2XXJ","MRA9K5DT","UGLDB735","6AFVGHQE"],
    36: ["87STH5SJ","QFLJEAVH","5V88R5N6","2JNYITMZ","FC6AVF4V","TWGAJYB5","S9JC4J9Y","9F7WA9TU"],
};

for (let [collId, paperKeys] of Object.entries(tiers)) {
    for (let key of paperKeys) {
        try {
            var item = await Zotero.Items.getByLibraryAndKeyAsync(libraryID, key);
            if (item) {
                item.addToCollection(parseInt(collId));
                await item.saveTx();
                added++;
            } else {
                errors.push(key + " not found");
            }
        } catch (e) {
            errors.push(key + ": " + e.message);
        }
    }
}

return "Added " + added + "/22 papers. Errors: " + (errors.length ? errors.join("; ") : "none");

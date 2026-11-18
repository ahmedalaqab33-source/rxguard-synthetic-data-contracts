# Independent base-R mechanics on the explicitly invented fixture only.
a <- commandArgs(trailingOnly=TRUE)
stopifnot(length(a)==1L)
f <- a[1]
meta <- read.csv(file.path(f,"synthetic_manifest.csv"),colClasses="character",na.strings="")
stopifnot(nrow(meta)==1,meta$scope=="SYNTHETIC",meta$invented=="TRUE",meta$contract_version=="synthetic-dictionary-event-0.1.0")
d <- read.csv(file.path(f,"invented_dictionary.csv"),colClasses="character",na.strings="")
e <- read.csv(file.path(f,"invented_events.csv"),colClasses="character",na.strings="")
stopifnot(all(d$scope=="SYNTHETIC"),all(e$scope=="SYNTHETIC"),!anyDuplicated(e$row_id),all(grepl("^INVENTED-",e$row_id)))
parse_time <- function(x) as.POSIXct(x,format="%Y-%m-%d %H:%M:%S",tz="UTC")
# UTC is a deterministic parser convention for invented naive times, not patient timezone inference.
asof <- parse_time(meta$as_of)
link <- units <- interval <- availability <- status <- character(nrow(e))
for(i in seq_len(nrow(e))) {
  key <- e$itemid[i]
  hits <- if(is.na(key)) integer(0) else which(!is.na(d$itemid) & d$itemid==key)
  n <- length(hits)
  link[i] <- if(is.na(key)) "MISSING_KEY" else if(n==0) "UNMATCHED_KEY" else if(n>1) "AMBIGUOUS_DICTIONARY_KEY" else if(is.na(d$linksto[hits])) "UNKNOWN_LINKSTO" else if(d$linksto[hits]!="inputevents") "LINKSTO_MISMATCH" else "UNIQUE_INPUTEVENTS_LINK"
  units[i] <- if(n!=1) "NOT_ASSESSED" else if(is.na(d$unitname[hits]) || is.na(e$amountuom[i])) "UNKNOWN" else if(d$unitname[hits]==e$amountuom[i]) "LITERAL_MATCH" else "LITERAL_MISMATCH"
  start <- parse_time(e$starttime[i]); end <- parse_time(e$endtime[i]); stored <- parse_time(e$storetime[i])
  interval[i] <- if(is.na(start)||is.na(end)) "UNKNOWN" else if(end<start) "REVERSED" else "NONREVERSED"
  availability[i] <- if(is.na(stored)) "UNKNOWN" else if(stored<=asof) "AT_OR_BEFORE" else "AFTER"
  status[i] <- if(is.na(e$statusdescription[i])) "MISSING_UNINTERPRETED" else "PRESENT_UNINTERPRETED"
}
keys <- d$itemid[!is.na(d$itemid)]
result <- c(dictionary_rows=nrow(d),dictionary_null_key_rows=sum(is.na(d$itemid)),dictionary_distinct_nonnull_keys=length(unique(keys)),event_rows=nrow(e),output_rows=length(link),dictionary_duplicate_keys=sum(table(keys)>1))
add <- function(field,values,states) setNames(vapply(states,function(s) sum(values==s),numeric(1)),paste(field,states,sep="."))
result <- c(result,add("linkage_state",link,c("MISSING_KEY","UNMATCHED_KEY","AMBIGUOUS_DICTIONARY_KEY","UNKNOWN_LINKSTO","LINKSTO_MISMATCH","UNIQUE_INPUTEVENTS_LINK")),add("unit_state",units,c("NOT_ASSESSED","UNKNOWN","LITERAL_MATCH","LITERAL_MISMATCH")),add("interval_state",interval,c("UNKNOWN","REVERSED","NONREVERSED")),add("availability_state",availability,c("UNKNOWN","AT_OR_BEFORE","AFTER")),add("status_state",status,c("MISSING_UNINTERPRETED","PRESENT_UNINTERPRETED")))
write.csv(data.frame(metric=names(result),count=as.integer(result)),file.path(f,"r_aggregates.csv"),row.names=FALSE,na="")
stopifnot(sum(table(link))==nrow(e))
cat("PASS: independent base-R invented aggregate mechanics\n")

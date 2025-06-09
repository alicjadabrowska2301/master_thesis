library(httr)
library(stringi)
library(dplyr)
library(rvest)

user_agent <- "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Function to extract links from main page
get_job_links <- function(url) {
  response <- GET(url, user_agent(user_agent))
  
  content <- content(response, as = "text", encoding = "UTF-8")
  
  links <- stri_extract_all_regex(content, "https://www\\.pracuj\\.pl/praca/[^\"]+")[[1]]
  valid_links <- unique(links)
  valid_links <- valid_links[!is.na(valid_links)]
  valid_links <- valid_links[!stri_detect_regex(valid_links, "true;so$|;wp$")]
  
  return(valid_links)
}

get_total_pages <- function(url) {
  response <- GET(url, user_agent(user_agent))
  
  content <- content(response, as = "parsed", encoding = "UTF-8") 
  
  total_pages <- html_element(content, 'span[data-test="top-pagination-max-page-number"]') %>%
    html_text(trim = TRUE) %>%
    as.integer()
  
  return(total_pages)
}



translate_text <- function(text, translations) {
  for (i in seq_along(translations)) {
    text <- stri_replace_all_fixed(text, names(translations)[i], translations[[i]], vectorize_all = FALSE)
  }
  return(text)
}

extract_technologies_by_type <- function(content, tech_type) {
  section <- html_elements(content, sprintf('div[data-test="section-technologies-%s"]', tech_type))
  
  if(length(section) == 0) {
    return(character(0))
  }
  
  technologies <- html_elements(section, sprintf('span[data-test="item-technologies-%s"]', tech_type)) %>%
    html_text(trim = TRUE)
  
  return(technologies)
}

scrape_job_page <- function(url) {
  Sys.sleep(2)
  
  response <- GET(url, user_agent(user_agent))
  
  content <- content(response, as = "parsed", encoding = "UTF-8")
  
  job_title <- html_element(content, 'h1[data-test="text-positionName"]') %>%
    html_text(trim = TRUE)
  
  company <- html_element(content, 'h2[data-test="text-employerName"]') %>%
    html_text(trim = TRUE) %>%
    stri_replace_all_fixed("O firmie", "") %>%
    stri_replace_all_fixed("About the company", "") %>%
    stri_trim_both()
  
  location <- html_element(content, 'div[data-test="offer-badge-title"]') %>%
    html_text(trim = TRUE)
  
  if(stri_detect_regex(location, ",")) {
    location <- stri_extract_last_regex(location, "[^,]+") %>% stri_trim_both()
  }
  
  salary_amounts <- html_elements(content, 'div[data-test="text-earningAmount"]') %>%
    html_text(trim = TRUE)
  
  
  salary_descriptions <- html_elements(content, 'div.sxxv7b6') %>%
    html_text(trim = TRUE) %>%
    translate_text(c("netto" = "net", "brutto" = "gross", "godz." = "hr.", "mies." = "mth."))
  
  contract_types <- html_element(content, 'li[data-test="sections-benefit-contracts"] div[data-test="offer-badge-title"]') %>%
    html_text(trim = TRUE) %>%
    translate_text(c(
      "umowa o pracę" = "contract of employment",
      "umowa o dzieło" = "contract for specific work",
      "umowa zlecenie" = "contract of mandate",
      "kontrakt B2B" = "B2B contract",
      "umowa na zastępstwo" = "substitution agreement",
      "umowa agencyjna" = "agency agreement",
      "umowa o pracę tymczasową" = "temporary staffing agreement",
      "umowa o staż / praktyki" = "internship / apprenticeship contract"
    ))
  
  work_schedule <- html_element(content, 'li[data-test="sections-benefit-work-schedule"] div[data-test="offer-badge-title"]') %>%
    html_text(trim = TRUE) %>%
    translate_text(c(
      "pełny etat" = "full-time",
      "część etatu" = "part time",
      "dodatkowa / tymczasowa" = "additional / temporary"
    ))
  
  employment_type <- html_element(content, 'li[data-test="sections-benefit-employment-type-name"] div[data-test="offer-badge-title"]') %>%
    html_text(trim = TRUE) %>%
    translate_text(c(
      "praktykant / stażysta" = "trainee",
      "asystent" = "assistant",
      "młodszy specjalista (Junior)" = "junior specialist (Junior)",
      "specjalista (Mid / Regular)" = "specialist (Mid / Regular)",
      "starszy specjalista (Senior)" = "senior specialist (Senior)",
      "ekspert" = "expert",
      "kierownik / koordynator" = "manager / supervisor",
      "menedżer" = "team manager",
      "dyrektor" = "director"
    ))
  
  work_mode <- html_element(content, 'li[data-scroll-id="work-modes"] div[data-test="offer-badge-title"]') %>%
    html_text(trim = TRUE) %>%
    translate_text(c(
      "praca stacjonarna" = "full office work",
      "praca hybrydowa" = "hybrid work",
      "praca zdalna" = "home office work",
      "praca mobilna" = "mobile work"
    ))
  
  
  # Check if specializations section exists
  has_specializations <- length(html_elements(content, 'li[data-test="it-specializations"]')) > 0
  
  specializations <- if (!has_specializations) {
    "No specialization listed"
  } else {
    html_element(content, 'li[data-test="it-specializations"] div.v1xz4nnx') %>%
      html_text(trim = TRUE)
  }
  
  expected_techs <- extract_technologies_by_type(content, "expected")
  optional_techs <- extract_technologies_by_type(content, "optional")
  
  technologies_expected <- if(length(expected_techs) > 0) stri_join(expected_techs, collapse = ", ") else "No expected technologies"
  technologies_optional <- if(length(optional_techs) > 0) stri_join(optional_techs, collapse = ", ") else "No optional technologies"
  
  list(
    title = job_title,
    company = company,
    location = location,
    salary_ranges = stri_join(salary_amounts, collapse = "; "),
    salary_description = stri_join(salary_descriptions, collapse = "; "),
    contract_types = contract_types,
    work_schedule = work_schedule,
    employment_type = employment_type,
    work_mode = work_mode,
    specializations = specializations,
    technologies_expected = technologies_expected,
    technologies_optional = technologies_optional,
    url = url
  )
}

main_scraper <- function() {
  base_url <- "https://it.pracuj.pl/praca/polska;ct,1?sal=1"
  total_pages <- get_total_pages(base_url)
  all_job_links <- c()
  
  for (page_num in 1:total_pages) {
    page_url <- sprintf("%s&pn=%d", base_url, page_num)
    cat("Scraping page:", page_num, "of", total_pages, "\n")
    job_links <- get_job_links(page_url)
    all_job_links <- c(all_job_links, job_links)
  }
  
  all_job_links <- unique(all_job_links)
  print(length(all_job_links))
  results <- list()
  
  for (i in seq_along(all_job_links)) {
    link <- all_job_links[i]
    tryCatch({
      job_data <- scrape_job_page(link)
      results[[length(results) + 1]] <- job_data
      cat(sprintf("Scraped %d/%d: %s\n", i, length(all_job_links), job_data$title))
    }, error = function(e) {
      cat("Error scraping:", link, "\n")
    })
  }
  
  df <- do.call(rbind, lapply(results, as.data.frame))
  return(df)
}

export_job_data <- function(df, base_filename = "job_offers") {
  timestamp <- format(Sys.time(), "%Y%m%d_%H%M")
  csv_filename <- stri_sprintf("%s_%s.csv", base_filename, timestamp)
  
  tryCatch({
    write.csv(df, csv_filename, row.names = FALSE, fileEncoding = "UTF-8")
    cat("CSV file saved:", csv_filename, "\n")
  }, error = function(e) {
    cat("Error saving CSV:", e$message, "\n")
  })
}

jobs_df_scrapped <- main_scraper()
export_job_data(jobs_df_scrapped)
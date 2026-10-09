/* libheif API declarations used by the CFFI bindings. */
typedef uint32_t heif_item_id;
typedef uint32_t heif_property_id;
struct heif_context;
struct heif_image_handle;
struct heif_image;
struct heif_reading_options;
struct heif_init_params;

enum heif_error_code { ... };
enum heif_suberror_code { ... };
struct heif_error {
    enum heif_error_code code;
    enum heif_suberror_code subcode;
    const char* message;
};

enum heif_filetype_result { heif_filetype_no, ... };
enum heif_colorspace { heif_colorspace_RGB, ... };
enum heif_chroma { heif_chroma_interleaved_RGB, heif_chroma_interleaved_RGBA, ... };
enum heif_channel { heif_channel_interleaved, ... };
enum heif_color_profile_type {
    heif_color_profile_type_rICC, heif_color_profile_type_prof, ...
};
enum heif_item_property_type {
    heif_item_property_type_transform_mirror,
    heif_item_property_type_transform_rotation,
    heif_item_property_type_transform_crop,
    ...
};
enum heif_transform_mirror_direction {
    heif_transform_mirror_direction_horizontal, ...
};

/* libheif allocates this versioned struct. Only access the common fields;
   never allocate it or depend on its compile-time size. */
struct heif_decoding_options {
    uint8_t version;
    uint8_t ignore_transformations;
    uint8_t convert_hdr_to_8bit;
    uint8_t strict_decoding;
    ...;
};

uint32_t heif_get_version_number(void);
struct heif_error heif_init(struct heif_init_params*);
void heif_deinit(void);
enum heif_filetype_result heif_check_filetype(const uint8_t*, int);
struct heif_context* heif_context_alloc(void);
void heif_context_free(struct heif_context*);
struct heif_error heif_context_read_from_memory_without_copy(
    struct heif_context*, const void*, size_t, const struct heif_reading_options*);
struct heif_error heif_context_get_primary_image_handle(
    struct heif_context*, struct heif_image_handle**);
void heif_image_handle_release(const struct heif_image_handle*);
int heif_image_handle_get_width(const struct heif_image_handle*);
int heif_image_handle_get_height(const struct heif_image_handle*);
int heif_image_handle_get_ispe_width(const struct heif_image_handle*);
int heif_image_handle_get_ispe_height(const struct heif_image_handle*);
int heif_image_handle_has_alpha_channel(const struct heif_image_handle*);
int heif_image_handle_get_luma_bits_per_pixel(const struct heif_image_handle*);
heif_item_id heif_image_handle_get_item_id(const struct heif_image_handle*);
int heif_item_get_transformation_properties(
    const struct heif_context*, heif_item_id, heif_property_id*, int);
enum heif_item_property_type heif_item_get_property_type(
    const struct heif_context*, heif_item_id, heif_property_id);
enum heif_transform_mirror_direction heif_item_get_property_transform_mirror(
    const struct heif_context*, heif_item_id, heif_property_id);
int heif_item_get_property_transform_rotation_ccw(
    const struct heif_context*, heif_item_id, heif_property_id);
void heif_item_get_property_transform_crop_borders(
    const struct heif_context*, heif_item_id, heif_property_id,
    int, int, int*, int*, int*, int*);
int heif_image_handle_get_number_of_metadata_blocks(
    const struct heif_image_handle*, const char*);
int heif_image_handle_get_list_of_metadata_block_IDs(
    const struct heif_image_handle*, const char*, heif_item_id*, int);
const char* heif_image_handle_get_metadata_type(
    const struct heif_image_handle*, heif_item_id);
size_t heif_image_handle_get_metadata_size(const struct heif_image_handle*, heif_item_id);
struct heif_error heif_image_handle_get_metadata(
    const struct heif_image_handle*, heif_item_id, void*);
enum heif_color_profile_type heif_image_handle_get_color_profile_type(
    const struct heif_image_handle*);
size_t heif_image_handle_get_raw_color_profile_size(const struct heif_image_handle*);
struct heif_error heif_image_handle_get_raw_color_profile(
    const struct heif_image_handle*, void*);
struct heif_decoding_options* heif_decoding_options_alloc(void);
void heif_decoding_options_free(struct heif_decoding_options*);
struct heif_error heif_decode_image(
    const struct heif_image_handle*, struct heif_image**,
    enum heif_colorspace, enum heif_chroma, const struct heif_decoding_options*);
const uint8_t* heif_image_get_plane_readonly(const struct heif_image*, enum heif_channel, int*);
void heif_image_release(const struct heif_image*);
